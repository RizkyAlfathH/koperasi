from email.mime import image
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
import datetime
from .utils import hitung_saldo

from .models import Penarikan, Simpanan, JenisSimpanan, HistoryTabungan, Anggota
from django.core.paginator import Paginator
from .forms import SimpananForm, PenarikanForm
from django.views.decorators.http import require_POST

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from num2words import num2words
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from admin_koperasi.utils import has_page_permission


# function (view): menampilkan daftar simpanan anggota
@login_required
def daftar_simpanan(request):

    if not has_page_permission(request.user, "simpanan"):
        messages.error(request, "Anda tidak memiliki izin untuk mengakses halaman ini")
        return redirect("dashboard")

    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'nomor')

    # ambil anggota aktif + filter search di level database
    try:
        anggotas = Anggota.objects.filter(status__iexact='aktif')

        if search_query:
            anggotas = anggotas.filter(
                Q(nama__icontains=search_query) |
                Q(nomor_anggota__icontains=search_query)
            )

        # sorting tetap di level database, bukan di python
        if sort_by == 'nama':
            anggotas = anggotas.order_by('nama')
        else:
            anggotas = anggotas.order_by('nomor_anggota')

    except Exception as e:
        messages.error(request, f"Gagal mengambil data anggota: {str(e)}")
        anggotas = Anggota.objects.none()

    # ✅ PAGINATION DULU sebelum hitung saldo — ini kuncinya
    paginator = Paginator(anggotas, 10)
    page_simpanan = paginator.get_page(request.GET.get('page_simpanan', 1))

    # anggota yang benar-benar perlu dihitung saldonya (hanya 10, bukan ratusan)
    anggota_ids = [a.pk for a in page_simpanan.object_list]

    # 1 query untuk semua saldo HistoryTabungan (pokok/wajib/sukarela)
    history_totals = (
        HistoryTabungan.objects
        .filter(anggota_id__in=anggota_ids)
        .values('anggota_id', 'jenis_simpanan_id', 'jenis_transaksi')
        .annotate(total=Sum('jumlah'))
    )

    # susun jadi dict: {anggota_id: {jenis_id: saldo}}
    saldo_map = {}
    for row in history_totals:
        aid = row['anggota_id']
        jid = row['jenis_simpanan_id']
        jt = row['jenis_transaksi']
        total = row['total'] or 0

        saldo_map.setdefault(aid, {})
        saldo_map[aid].setdefault(jid, 0)

        if jt == 'SETOR':
            saldo_map[aid][jid] += total
        elif jt == 'TARIK':
            saldo_map[aid][jid] -= total
        elif jt == 'KOREKSI':
            saldo_map[aid][jid] += total

    # 1 query untuk semua dana_sosial (dari model Simpanan)
    dana_sosial_totals = (
        Simpanan.objects
        .filter(anggota_id__in=anggota_ids)
        .values('anggota_id')
        .annotate(total=Sum('dana_sosial'))
    )
    dana_sosial_map = {row['anggota_id']: row['total'] or 0 for row in dana_sosial_totals}

    # bangun data_list HANYA untuk anggota di halaman ini
    data_list = []
    for anggota in page_simpanan.object_list:
        saldo_anggota = saldo_map.get(anggota.pk, {})
        data_list.append({
            'nomor_anggota': anggota.nomor_anggota,
            'nama_anggota': anggota.nama,
            'total_pokok': saldo_anggota.get(1, 0),
            'total_wajib': saldo_anggota.get(2, 0),
            'total_sukarela': saldo_anggota.get(3, 0),
            'total_dana_sosial': dana_sosial_map.get(anggota.pk, 0),
        })

    return render(request, "daftar_simpanan.html", {
        'data': data_list,
        'page_obj': page_simpanan,
        'param': 'page_simpanan',
        'search_query': search_query,
        'sort_by': sort_by,
    })


# function (view): menambahkan data simpanan baru
@login_required
@transaction.atomic
def tambah_simpanan(request):

    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    anggota_label = None

    if request.method == "POST":
        anggota_id = request.POST.get("anggota")
        tanggal_str = request.POST.get("tanggal")
        jumlah_baris = int(request.POST.get("jumlah_baris", 1))

        base_form = SimpananForm(request.POST)

        if anggota_id:
            from anggota.models import Anggota
            try:
                anggota_obj = Anggota.objects.get(pk=anggota_id)
                anggota_label = f"{anggota_obj.nomor_anggota} - {anggota_obj.nama}"
            except:
                anggota_obj = None
        else:
            anggota_obj = None

        baris_data = []
        has_error = False

        for i in range(jumlah_baris):
            jenis_id = request.POST.get(f"jenis_simpanan_{i}")
            jumlah_raw = request.POST.get(f"jumlah_{i}", "0")
            dana_raw = request.POST.get(f"dana_sosial_{i}", "0")

            import re
            jumlah = int(re.sub(r'\D', '', jumlah_raw) or 0)
            dana = int(re.sub(r'\D', '', dana_raw) or 0)

            baris_data.append({
                "index": i,
                "jenis_id": jenis_id,
                "jumlah": jumlah,
                "dana_sosial": dana,
            })

        from anggota.models import Anggota
        import datetime
        from .models import JenisSimpanan

        try:
            tanggal = datetime.date.fromisoformat(tanggal_str)
        except (TypeError, ValueError):
            tanggal = None

        if not anggota_obj or not tanggal:
            messages.error(request, "Anggota dan tanggal wajib diisi.")
            has_error = True

        if not has_error:
            try:
                # cek duplikat dulu sebelum simpan apapun
                duplikat = []
                for baris in baris_data:
                    jenis = JenisSimpanan.objects.get(pk=baris["jenis_id"])
                    sudah_ada = Simpanan.objects.filter(
                        anggota=anggota_obj,
                        jenis_simpanan=jenis,
                        tanggal__month=tanggal.month,
                        tanggal__year=tanggal.year
                    ).exists()
                    if sudah_ada:
                        duplikat.append(jenis.nama)

                if duplikat:
                    messages.error(request, f"Simpanan bulan ini sudah ada: {', '.join(duplikat)}.")
                else:
                    for baris in baris_data:
                        jenis = JenisSimpanan.objects.get(pk=baris["jenis_id"])
                        simpanan = Simpanan(
                            anggota=anggota_obj,
                            admin=request.user,
                            jenis_simpanan=jenis,
                            tanggal=tanggal,
                            jumlah=baris["jumlah"],
                            dana_sosial=baris["dana_sosial"],
                        )
                        simpanan.save()

                    messages.success(request, f"{len(baris_data)} simpanan berhasil ditambahkan.")
                    return redirect("simpanan:daftar_simpanan")

            except Exception as e:
                messages.error(request, f"Gagal menyimpan: {str(e)}")

        form = SimpananForm(request.POST)

    else:
        form = SimpananForm()

    return render(request, "form/simpanan_form.html", {
        "form": form,
        "anggota_label": anggota_label,
    })


# function (view API): cek apakah dana sosial wajib diisi
@login_required
def cek_dana_sosial(request):

    # ambil parameter dari request GET
    anggota_id = request.GET.get('anggota')
    jenis_id = request.GET.get('jenis')
    tanggal_str = request.GET.get('tanggal')

    # validasi parameter wajib
    if not anggota_id or not jenis_id or not tanggal_str:
        return JsonResponse(
            {'wajib': False, 'error': 'Parameter tidak lengkap'},
            status=400
        )

    # parsing string ke date (method datetime)
    try:
        tanggal = datetime.datetime.strptime(tanggal_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse(
            {'wajib': False, 'error': 'Format tanggal tidak valid, gunakan YYYY-MM-DD'},
            status=400
        )

    # query database untuk cek apakah sudah bayar bulan ini
    try:
        sudah_bayar = Simpanan.objects.filter(
            anggota_id=anggota_id,
            jenis_simpanan_id=jenis_id,
            tanggal__month=tanggal.month,
            tanggal__year=tanggal.year
        ).exists()  # method queryset: cek keberadaan data

    except Exception as e:
        return JsonResponse(
            {'wajib': False, 'error': f'Gagal mengecek data: {str(e)}'},
            status=500
        )

    # return response JSON
    return JsonResponse({
        'wajib': not sudah_bayar
    })

# function (view): menampilkan ringkasan saldo simpanan per anggota
@login_required
def simpanan_anggota(request, nomor_anggota):

    # ambil objek anggota dari database
    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)

    # list (objek): menampung data saldo per jenis
    data_saldo = []

    # ambil semua jenis simpanan
    try:
        jenis_list = JenisSimpanan.objects.all()
    except Exception as e:
        messages.error(request, f"Gagal memuat jenis simpanan: {str(e)}")
        jenis_list = []

    # loop: iterasi setiap jenis simpanan
    for jenis in jenis_list:
        try:
            # aggregate: total setor dari model simpanan
            total_setor = (
                Simpanan.objects.filter(
                    anggota=anggota,
                    jenis_simpanan=jenis
                ).aggregate(total=Sum('jumlah'))['total'] or 0
            )

            # aggregate: total tarik dari model penarikan
            total_tarik = (
                Penarikan.objects.filter(
                    anggota=anggota,
                    jenis_simpanan=jenis
                ).aggregate(total=Sum('jumlah'))['total'] or 0
            )

            # hitung saldo
            saldo = total_setor - total_tarik

            # ambil transaksi terakhir dari history
            last_transaksi = HistoryTabungan.objects.filter(
                anggota=anggota,
                jenis_simpanan=jenis
            ).order_by('-id').first()

            # simpan ke list
            data_saldo.append({
                'jenis': jenis.get_nama_jenis_display(),
                'jenis_id': jenis.id,
                'saldo': saldo,
                'last_id': last_transaksi.id if last_transaksi else None
            })

        except Exception as e:
            # handling error per jenis
            messages.warning(request, f"Gagal memuat saldo jenis {jenis}: {str(e)}")
            continue

    # jika semua saldo nol, kosongkan data agar template menampilkan pesan
    if all(item['saldo'] == 0 for item in data_saldo):
        data_saldo = []

    # render template
    return render(request, "detail/simpanan_anggota.html", {
        'username': request.user.username,
        'role': request.user.role,
        'anggota': anggota,
        'data_saldo': data_saldo,
    })


# function (view): menampilkan detail riwayat simpanan per jenis
@login_required
def detail_simpanan(request, nomor_anggota, jenis_id):

    # ambil objek anggota dan jenis simpanan
    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)
    jenis_simpanan = get_object_or_404(JenisSimpanan, id=jenis_id)

    # ambil parameter filter tanggal dari request
    tanggal_filter = request.GET.get("tanggal")

    # blok: query history tabungan
    try:
        history_qs = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis_simpanan
        ).order_by("-tanggal", "-id")

        # filter berdasarkan tanggal jika ada input
        if tanggal_filter:
            try:
                tanggal = datetime.datetime.strptime(tanggal_filter, "%Y-%m-%d").date()
                history_qs = history_qs.filter(tanggal=tanggal)
            except ValueError:
                messages.warning(request, "Format tanggal tidak valid, filter diabaikan")

    except Exception as e:
        messages.error(request, f"Gagal memuat riwayat transaksi: {str(e)}")
        history_qs = HistoryTabungan.objects.none()

    # pagination (objek paginator)
    paginator = Paginator(history_qs, 5)
    page_history = paginator.get_page(request.GET.get("page_history", 1))

    # blok: hitung saldo berdasarkan history
    try:
        qs = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis_simpanan
        )

        # aggregate: total setor
        setor = qs.filter(
            jenis_transaksi='SETOR'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        # aggregate: total tarik
        tarik = qs.filter(
            jenis_transaksi='TARIK'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        # aggregate: total koreksi
        koreksi = qs.filter(
            jenis_transaksi='KOREKSI'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        # hitung saldo akhir
        saldo_jenis = setor - tarik + koreksi

    except Exception as e:
        messages.error(request, f"Gagal menghitung saldo: {str(e)}")
        saldo_jenis = 0

    # context (objek dict): dikirim ke template
    context = {
        "anggota": anggota,
        "jenis_simpanan": jenis_simpanan,
        "history": page_history,
        "page_obj": page_history,
        "param": "page_history",
        "saldo_jenis": saldo_jenis,
        "tanggal_filter": tanggal_filter,
    }

    # render template
    return render(request, "detail/detail_simpanan.html", context)


# function (view): menambahkan data penarikan
@login_required
@transaction.atomic
def tambah_penarikan(request, nomor_anggota, jenis):

    # validasi role user
    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    # ambil objek anggota dan jenis simpanan
    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)
    jenis_obj = get_object_or_404(JenisSimpanan, pk=jenis)

    # hitung saldo menggunakan helper function
    try:
        saldo = hitung_saldo(anggota, jenis_obj)
    except Exception as e:
        messages.error(request, f"Gagal menghitung saldo: {str(e)}")
        return redirect("simpanan:simpanan_anggota", nomor_anggota)

    # jika request POST (submit form)
    if request.method == "POST":

        # objek form dengan parameter tambahan
        form = PenarikanForm(
            request.POST,
            anggota=anggota,
            jenis_simpanan=jenis_obj
        )

        # validasi form
        if form.is_valid():
            try:
                # commit=False agar bisa set field tambahan
                penarikan = form.save(commit=False)

                # set relasi
                penarikan.anggota = anggota
                penarikan.jenis_simpanan = jenis_obj
                penarikan.admin = request.user

                # simpan ke database
                penarikan.save()

                messages.success(request, "Penarikan berhasil")
                return redirect("simpanan:simpanan_anggota", nomor_anggota)

            except Exception as e:
                messages.error(request, f"Gagal menyimpan penarikan: {str(e)}")

        else:
            # jika form tidak valid
            messages.error(request, "Form tidak valid, periksa kembali isian Anda")

    else:
        # jika GET, tampilkan form kosong
        form = PenarikanForm(
            anggota=anggota,
            jenis_simpanan=jenis_obj
        )

    # render template form
    return render(request, "form/penarikan_form.html", {
        "form": form,
        "anggota": anggota,
        "saldo": saldo,
        "jenis_simpanan": jenis_obj.nama_jenis,
    })


# function (view): autocomplete anggota untuk kebutuhan select2 / ajax search
@login_required
def autocomplete_anggota(request):
    # objek: request, mengambil parameter query 'term'
    term = request.GET.get('term', '')

    try:
        # query (orm): mengambil data anggota aktif berdasarkan nama (contains)
        anggota_list = Anggota.objects.filter(
            nama__icontains=term,
            status='aktif'
        )[:10]  # slicing: membatasi hasil maksimal 10 data

        # response: json berisi hasil untuk autocomplete
        return JsonResponse({
            "results": [
                {
                    "id": a.pk,  # atribut objek model
                    "text": f"{a.nomor_anggota} - {a.nama}"  # format tampilan
                }
                for a in anggota_list  # list comprehension
            ]
        })

    except Exception as e:
        # error handling: jika query gagal, kirim response kosong + pesan error
        return JsonResponse(
            {
                "results": [],
                "error": f"Gagal mencari anggota: {str(e)}"
            },
            status=500
        )


# function (view): menampilkan detail transaksi dari history tabungan
@login_required
def detail_transaksi(request, id):
    # query (orm): mengambil objek history tabungan berdasarkan id
    # jika tidak ditemukan otomatis 404 (fungsi bawaan django)
    transaksi = get_object_or_404(HistoryTabungan, id=id)

    # render template dengan context data transaksi
    return render(request, "detail/detail_transaksi.html", {
        "transaksi": transaksi  # objek dikirim ke template
    })


@login_required
def download_kwitansi(request, history_id):
    trx = get_object_or_404(HistoryTabungan, id=history_id)  # ✅ sudah ada

    anggota = trx.anggota
    tanggal = trx.tanggal
    jumlah = trx.jumlah
    jenis_simpanan = trx.jenis_simpanan

    # ✅ Validasi: pastikan data wajib tidak kosong
    if not anggota:
        messages.error(request, "Data anggota tidak ditemukan")
        return redirect("dashboard")

    if not jumlah or jumlah <= 0:
        messages.error(request, "Jumlah transaksi tidak valid")
        return redirect("dashboard")

    nama_simpanan = (
        jenis_simpanan.get_nama_jenis_display()
        if jenis_simpanan else "Tabungan"
    )

    if trx.jenis_transaksi == HistoryTabungan.SETOR:
        judul = "BUKTI PENERIMAAN KAS"
        pihak_label = "Diterima dari"
        pemberi = "(...........................)"
        penerima = f"({anggota.nama})"
        filename = f"kwitansi_setoran_{anggota.nama}"

    elif trx.jenis_transaksi == HistoryTabungan.TARIK:
        judul = "BUKTI PENGELUARAN KAS"
        pihak_label = "Diberikan kepada"
        pemberi = "(...........................)"
        penerima = f"({anggota.nama})"
        filename = f"kwitansi_penarikan_{anggota.nama}"

    else:
        judul = "BUKTI TRANSAKSI KAS"
        pihak_label = "Pihak"
        pemberi = "(...........................)"
        penerima = "(...........................)"
        filename = f"kwitansi_{anggota.nama}"

    try:  # ✅ tangkap error saat generate PDF (reportlab)
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'

        width, height = 25.1 * cm, 10.7 * cm
        c = canvas.Canvas(response, pagesize=(width, height))

        c.drawImage(
            "static/image/logo_koperasiK.jpeg",
            0.8 * cm, height - 2.6 * cm,
            width=2.2 * cm, height=2.2 * cm
        )

        text_x = 3.4 * cm
        header_right_limit = width - 7.0 * cm
        shift_left = 3.5 * cm
        header_center_x = (text_x + header_right_limit) / 2 - shift_left

        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(header_center_x, height - 0.9 * cm, "K P R I SMK NEGERI 11 KOTA BANDUNG")

        c.setFont("Helvetica", 9)
        c.drawCentredString(header_center_x, height - 1.3 * cm, "( K O P A S M E N )")

        c.setFont("Helvetica", 8)
        c.drawCentredString(header_center_x, height - 1.9 * cm, "Jl. Budi Cilember Telp. 6652442 Bandung")
        c.drawCentredString(header_center_x, height - 2.2 * cm, "HAK BADAN HUKUM NO. : 9749/BH/KWK-10/21")
        c.drawCentredString(header_center_x, height - 2.5 * cm, "TANGGAL : 18 NOVEMBER 1991")

        right_block_x = width - 6.5 * cm
        right_block_top = height - 0.9 * cm

        c.setFont("Helvetica-Bold", 11)
        c.drawString(right_block_x, right_block_top, judul)

        c.setFont("Helvetica", 9)
        c.drawString(right_block_x, height - 1.5 * cm, "UNIT :")
        c.drawString(right_block_x, height - 2.0 * cm, "K.M. NO. ................................")

        left_x  = 0.9 * cm
        right_x = width - 13.0 * cm

        c.setLineWidth(2)
        c.line(left_x, height - 2.7 * cm, right_x, height - 2.7 * cm)

        c.setLineWidth(1)
        c.line(left_x, height - 2.8 * cm, right_x, height - 2.8 * cm)

        c.setFont("Helvetica", 10)
        c.drawString(1.2 * cm, height - 3.6 * cm, f"{pihak_label} :")
        c.drawString(4.8 * cm, height - 3.6 * cm, anggota.nama)

        line_start_x = 4.7 * cm
        line_end_x   = 12.8 * cm
        line_y       = height - 3.8 * cm
        c.line(line_start_x, line_y, line_end_x, line_y)

        c.setFont("Helvetica", 9)
        c.drawString(line_end_x + 0.2 * cm, height - 3.6 * cm, "(Anggota / Bukan Anggota)")

        c.setFont("Helvetica", 10)
        c.drawString(1.2 * cm, height - 4.5 * cm, "Jumlah    :  Rp.")

        box_y_top = height - 4.7 * cm
        box_height = 0.6 * cm
        box3_height = 0.6 * cm
        gap_x = 0.6 * cm
        gap_y = 0.8 * cm

        box1_x = 3.9 * cm
        box1_w = 3.8 * cm
        c.rect(box1_x, box_y_top, box1_w, box_height)

        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(
            box1_x + box1_w / 2,
            box_y_top + (box_height / 2) - 3,
            f"{int(jumlah):,}".replace(",", ".")
        )

        box2_x = box1_x + box1_w + gap_x
        box2_w = 10.2 * cm
        c.rect(box2_x, box_y_top, box2_w, box_height)

        c.setFont("Helvetica", 9)
        c.drawString(
            box2_x + 0.2 * cm,
            box_y_top + (box_height / 2) - 3,
            f"{num2words(int(jumlah), lang='id').capitalize()} rupiah"
        )

        box3_x = 3.0 * cm
        box3_y = box_y_top - gap_y
        box3_w = 15.5 * cm
        c.rect(box3_x, box3_y, box3_w, box3_height)

        c.setFont("Helvetica", 10)
        text_y = height - 6.0 * cm
        line_gap = 0.1 * cm

        c.drawString(1.2 * cm, text_y, "Untuk :")

        c.setDash(1, 2)
        c.line(3.0 * cm, text_y - line_gap, 18.5 * cm, text_y - line_gap)
        c.line(3.0 * cm, text_y - line_gap - 0.6 * cm, 18.5 * cm, text_y - line_gap - 0.5 * cm)
        c.setDash()

        c.setFont("Helvetica", 9)
        c.drawRightString(width - 1.2 * cm, 4.8 * cm, f"Bandung, {tanggal.strftime('%d %B %Y')}")

        c.drawCentredString(2.2 * cm, 2.8 * cm, pemberi)
        c.drawCentredString(2.2 * cm, 2.5 * cm, "Bendahara")

        c.drawCentredString(width - 3.2 * cm, 2.8 * cm, penerima)
        c.drawCentredString(width - 3.2 * cm, 2.5 * cm, "Penerima")

        data = [
            ["DIISI OLEH BAGIAN PEMBUKUAN", "No. Perkiraan", "Debit", "Kredit", "Paraf"],
            ["Tanggal Pembukuan :", "", "", "", ""],
            ["Hal. Buku Harian :", "", "", "", ""],
        ]

        table = Table(
            data,
            colWidths=[6.5*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3.0*cm],
            rowHeights=[0.5*cm, 0.5*cm, 0.5*cm]
        )

        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 1.3, colors.black),
            ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONT", (0,1), (0,-1), "Helvetica-Bold"),
            ("ALIGN", (1,0), (-1,0), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("SPAN", (4,1), (4,2)),
        ]))

        table.wrapOn(c, width, height)
        table.drawOn(c, 0.9 * cm, 0.6 * cm)

        c.save()
        return response

    except Exception as e:  # ✅ tangkap error generate PDF
        messages.error(request, f"Gagal membuat kwitansi PDF: {str(e)}")
        return redirect("simpanan:detail_transaksi", history_id)

from .utils_import import proses_file_import

# ================================================================
# VIEW 1: halaman upload file
# ================================================================
@login_required
def import_simpanan(request):

    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    if request.method == "POST":
        file    = request.FILES.get("file_import")
        tanggal_str = request.POST.get("tanggal", "")

        # --- validasi file ---
        if not file:
            messages.error(request, "File wajib diupload.")
            return render(request, "form/import_simpanan.html")

        if not file.name.endswith('.xlsx'):
            messages.error(request, "File harus berformat .xlsx")
            return render(request, "form/import_simpanan.html")

        # --- validasi tanggal ---
        try:
            tanggal = datetime.date.fromisoformat(tanggal_str)
        except (TypeError, ValueError):
            messages.error(request, "Tanggal tidak valid.")
            return render(request, "form/import_simpanan.html")

        # --- proses file ---
        rows, error = proses_file_import(file)
        if error:
            messages.error(request, error)
            return render(request, "form/import_simpanan.html")

        # hitung ringkasan untuk ditampilkan di preview
        jumlah_cocok      = sum(1 for r in rows if r['cocok'])
        jumlah_tidak_cocok = sum(1 for r in rows if not r['cocok'])

        return render(request, "form/preview_import.html", {
            "rows"              : rows,
            "tanggal"           : tanggal,
            "tanggal_str"       : tanggal_str,
            "jumlah_cocok"      : jumlah_cocok,
            "jumlah_tidak_cocok": jumlah_tidak_cocok,
            "semua_anggota"     : Anggota.objects.filter(status='aktif').order_by('nama'),
        })

    return render(request, "form/import_simpanan.html")


# ================================================================
# VIEW 2: simpan data setelah user konfirmasi preview
# ================================================================
@login_required
@transaction.atomic
@login_required
@transaction.atomic
def proses_import_simpanan(request):

    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("simpanan:import_simpanan")

    # DEBUG: print semua POST data
    print("=== DEBUG POST DATA ===")
    for key, val in request.POST.items():
        print(f"  {key} = {val}")
    print("======================")

    try:
        tanggal = datetime.date.fromisoformat(request.POST.get("tanggal", ""))
    except (TypeError, ValueError):
        messages.error(request, "Tanggal tidak valid.")
        return redirect("simpanan:import_simpanan")

    jumlah_baris = int(request.POST.get("jumlah_baris", 0))
    print(f"jumlah_baris = {jumlah_baris}")

    berhasil = 0
    dilewati = 0
    duplikat = 0
    gagal    = []

    for i in range(jumlah_baris):
        skip       = request.POST.get(f"skip_{i}")
        anggota_id = request.POST.get(f"anggota_id_{i}", "").strip()

        print(f"\n--- baris {i} ---")
        print(f"  skip={skip}")
        print(f"  anggota_id={anggota_id}")
        print(f"  pokok={request.POST.get(f'pokok_{i}')}")
        print(f"  wajib={request.POST.get(f'wajib_{i}')}")
        print(f"  sukarela={request.POST.get(f'sukarela_{i}')}")
        print(f"  id_pokok={request.POST.get(f'id_pokok_{i}')}")
        print(f"  id_wajib={request.POST.get(f'id_wajib_{i}')}")
        print(f"  id_sukarela={request.POST.get(f'id_sukarela_{i}')}")

        if skip == "1":
            dilewati += 1
            continue

        if not anggota_id:
            dilewati += 1
            continue

        try:
            anggota = Anggota.objects.get(nomor_anggota=anggota_id)
        except Anggota.DoesNotExist:
            gagal.append(f"Baris {i+1}: anggota '{anggota_id}' tidak ditemukan")
            continue

        def nilai(key):
            try:
                return float(request.POST.get(key, 0) or 0)
            except ValueError:
                return 0

        data_simpanan = [
            {
                'jenis_id': request.POST.get(f"id_pokok_{i}"),
                'jumlah'  : nilai(f"pokok_{i}"),
                'dansos'  : 0,
            },
            {
                'jenis_id': request.POST.get(f"id_wajib_{i}"),
                'jumlah'  : nilai(f"wajib_{i}"),
                'dansos'  : nilai(f"dansos_{i}"),
            },
            {
                'jenis_id': request.POST.get(f"id_sukarela_{i}"),
                'jumlah'  : nilai(f"sukarela_{i}"),
                'dansos'  : 0,
            },
        ]

        for s in data_simpanan:
            if s['jumlah'] <= 0 or not s['jenis_id']:
                print(f"  SKIP jenis_id={s['jenis_id']} jumlah={s['jumlah']}")
                continue

            try:
                jenis = JenisSimpanan.objects.get(pk=s['jenis_id'])
            except JenisSimpanan.DoesNotExist:
                print(f"  jenis {s['jenis_id']} tidak ditemukan di DB")
                continue

            sudah_ada = Simpanan.objects.filter(
                anggota=anggota,
                jenis_simpanan=jenis,
                tanggal__month=tanggal.month,
                tanggal__year=tanggal.year,
            ).exists()

            if sudah_ada:
                print(f"  DUPLIKAT: {anggota.nama} {jenis.nama_jenis}")
                duplikat += 1
                continue

            try:
                Simpanan.objects.create(
                    anggota        = anggota,
                    admin          = request.user,
                    jenis_simpanan = jenis,
                    tanggal        = tanggal,
                    jumlah         = s['jumlah'],
                    dana_sosial    = s['dansos'],
                )
                print(f"  ✅ SIMPAN: {anggota.nama} {jenis.nama_jenis} {s['jumlah']}")
                berhasil += 1
            except Exception as e:
                print(f"  ❌ ERROR SIMPAN: {e}")
                gagal.append(f"{anggota.nama} ({jenis.nama_jenis}): {e}")

    print(f"\n=== HASIL: berhasil={berhasil} dilewati={dilewati} duplikat={duplikat} gagal={len(gagal)} ===")

    if berhasil:
        messages.success(request, f"✅ {berhasil} simpanan berhasil diimport.")
    if duplikat:
        messages.warning(request, f"⚠️ {duplikat} simpanan dilewati karena sudah ada di bulan yang sama.")
    if dilewati:
        messages.info(request, f"ℹ️ {dilewati} baris dilewati.")
    for f in gagal:
        messages.error(request, f"❌ {f}")

    return redirect("simpanan:daftar_simpanan")