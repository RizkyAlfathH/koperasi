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


@login_required
def daftar_simpanan(request):
    if not has_page_permission(request.user, "simpanan"):
        messages.error(request, "Anda tidak memiliki izin untuk mengakses halaman ini")
        return redirect("dashboard")

    data_list = []
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'nomor')

    try:
        anggotas = Anggota.objects.filter(status__iexact='aktif')
        if search_query:
            anggotas = anggotas.filter(
                Q(nama__icontains=search_query) |
                Q(nomor_anggota__icontains=search_query)
            )
    except Exception as e:
        messages.error(request, f"Gagal mengambil data anggota: {str(e)}")
        anggotas = Anggota.objects.none()

    # ✅ get_saldo sekarang pakai HistoryTabungan sebagai sumber kebenaran
    def get_saldo(anggota, jenis_id):
        try:
            qs = HistoryTabungan.objects.filter(
                anggota=anggota,
                jenis_simpanan_id=jenis_id
            )
            setor = qs.filter(
                jenis_transaksi='SETOR'
            ).aggregate(total=Sum('jumlah'))['total'] or 0

            tarik = qs.filter(
                jenis_transaksi='TARIK'
            ).aggregate(total=Sum('jumlah'))['total'] or 0

            koreksi = qs.filter(
                jenis_transaksi='KOREKSI'
            ).aggregate(total=Sum('jumlah'))['total'] or 0  # sudah negatif

            return setor - tarik + koreksi
        except Exception:
            return 0

    for anggota in anggotas:
        try:
            data_list.append({
                'nomor_anggota': anggota.nomor_anggota,
                'nama_anggota': anggota.nama,
                'total_pokok': get_saldo(anggota, 1),
                'total_wajib': get_saldo(anggota, 2),
                'total_sukarela': get_saldo(anggota, 3),
                'total_dana_sosial': (
                    Simpanan.objects.filter(anggota=anggota)
                    .aggregate(total=Sum('dana_sosial'))['total'] or 0
                ),
            })
        except Exception as e:
            messages.warning(request, f"Gagal memuat data anggota {anggota.nama}: {str(e)}")
            continue

    if sort_by == 'nama':
        data_list.sort(key=lambda x: x['nama_anggota'])
    else:
        data_list.sort(key=lambda x: x['nomor_anggota'])

    paginator = Paginator(data_list, 10)
    page_simpanan = paginator.get_page(
        request.GET.get('page_simpanan', 1)
    )

    return render(request, "daftar_simpanan.html", {
        'data': page_simpanan,
        'page_obj': page_simpanan,
        'param': 'page_simpanan',
        'search_query': search_query,
        'sort_by': sort_by,
    })


@login_required
@transaction.atomic
def tambah_simpanan(request):
    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    anggota_label = None

    if request.method == "POST":
        form = SimpananForm(request.POST)

        if form.is_valid():
            try:
                simpanan = form.save(commit=False)
                simpanan.admin = request.user
                simpanan.save()
                messages.success(request, "Simpanan berhasil ditambahkan")
                return redirect("simpanan:daftar_simpanan")
            except Exception as e:
                messages.error(request, f"Gagal menyimpan simpanan: {str(e)}")

        else:
            # 🔥 ambil ulang label anggota
            anggota_id = request.POST.get("anggota")
            if anggota_id:
                from anggota.models import Anggota
                try:
                    anggota = Anggota.objects.get(pk=anggota_id)
                    anggota_label = f"{anggota.nomor_anggota} - {anggota.nama}"
                except:
                    pass

            messages.error(request, "Form tidak valid, periksa kembali isian Anda")

    else:
        form = SimpananForm()

    return render(request, "form/simpanan_form.html", {
        "form": form,
        "anggota_label": anggota_label
    })


@login_required
def cek_dana_sosial(request):
    anggota_id = request.GET.get('anggota')
    jenis_id = request.GET.get('jenis')
    tanggal_str = request.GET.get('tanggal')

    if not anggota_id or not jenis_id or not tanggal_str:
        return JsonResponse({'wajib': False, 'error': 'Parameter tidak lengkap'}, status=400)  # ✅ tambah status code & pesan

    try:  # ✅ tangkap error parsing tanggal
        tanggal = datetime.datetime.strptime(tanggal_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({'wajib': False, 'error': 'Format tanggal tidak valid, gunakan YYYY-MM-DD'}, status=400)  # ✅ sebelumnya langsung crash

    try:  # ✅ tangkap error query database
        sudah_bayar = Simpanan.objects.filter(
            anggota_id=anggota_id,
            jenis_simpanan_id=jenis_id,
            tanggal__month=tanggal.month,
            tanggal__year=tanggal.year
        ).exists()
    except Exception as e:
        return JsonResponse({'wajib': False, 'error': f'Gagal mengecek data: {str(e)}'}, status=500)

    return JsonResponse({'wajib': not sudah_bayar})

@login_required
@require_POST
@transaction.atomic
def hapus_transaksi_terakhir(request, nomor_anggota, jenis_id):
    try:
        anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)
        jenis = get_object_or_404(JenisSimpanan, id=jenis_id)

        transaksi_terakhir = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis,
            jenis_transaksi='SETOR'
        ).order_by('-id').first()

        if not transaksi_terakhir:
            return JsonResponse({
                "success": False,
                "message": f"Tidak ada transaksi SETOR untuk simpanan {jenis.get_nama_jenis_display()}."
            }, status=404)

        jumlah_koreksi = transaksi_terakhir.jumlah

        # Cari simpanan yang matching
        simpanan_terkait = Simpanan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis,
            jumlah=jumlah_koreksi,
            tanggal=transaksi_terakhir.tanggal
        ).order_by('-id').first()

        if simpanan_terkait:
            # Hapus simpanan → lalu hapus SETOR-nya langsung
            # TIDAK perlu buat KOREKSI, karena simpanannya memang dihapus
            simpanan_terkait.delete()
            transaksi_terakhir.delete()
        else:
            # Simpanan sudah tidak ada tapi history masih ada
            # Baru pakai KOREKSI untuk nol-kan
            HistoryTabungan.objects.create(
                anggota=anggota,
                jenis_simpanan=jenis,
                tanggal=datetime.date.today(),
                jenis_transaksi='KOREKSI',
                jumlah=-jumlah_koreksi
            )

        return JsonResponse({
            "success": True,
            "message": f"Transaksi terakhir simpanan {jenis.get_nama_jenis_display()} berhasil dihapus.",
            "jumlah": str(jumlah_koreksi)
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=400)

# hapus_simpanan
@login_required
@require_POST
@transaction.atomic
def hapus_simpanan(request, nomor_anggota):
    try:
        anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)

        semua_simpanan = Simpanan.objects.filter(anggota=anggota)

        if not semua_simpanan.exists():
            return JsonResponse({
                "success": False,
                "message": "Tidak ada data simpanan untuk anggota ini."
            }, status=404)

        jenis_list = JenisSimpanan.objects.all()
        history_bulk = []

        for jenis in jenis_list:
            qs = HistoryTabungan.objects.filter(
                anggota=anggota,
                jenis_simpanan=jenis
            )

            setor = qs.filter(
                jenis_transaksi='SETOR'
            ).aggregate(total=Sum('jumlah'))['total'] or 0

            tarik = qs.filter(
                jenis_transaksi='TARIK'
            ).aggregate(total=Sum('jumlah'))['total'] or 0

            koreksi = qs.filter(
                jenis_transaksi='KOREKSI'
            ).aggregate(total=Sum('jumlah'))['total'] or 0

            # Hitung saldo bersih jenis ini
            saldo_bersih = setor - tarik + koreksi

            # Hanya buat KOREKSI kalau saldo tidak nol
            if saldo_bersih != 0:
                history_bulk.append(HistoryTabungan(
                    anggota=anggota,
                    jenis_simpanan=jenis,
                    tanggal=datetime.date.today(),
                    jenis_transaksi="KOREKSI",
                    jumlah=-saldo_bersih  # nol-kan saldo jenis ini
                ))

        if history_bulk:
            HistoryTabungan.objects.bulk_create(history_bulk)

        semua_simpanan.delete()

        return JsonResponse({
            "success": True,
            "message": f"Semua simpanan {anggota.nama} berhasil dihapus."
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=400)

@login_required
def simpanan_anggota(request, nomor_anggota):
    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)

    data_saldo = []

    try:
        jenis_list = JenisSimpanan.objects.all()
    except Exception as e:
        messages.error(request, f"Gagal memuat jenis simpanan: {str(e)}")
        jenis_list = []

    for jenis in jenis_list:
        try:
            total_setor = (
                Simpanan.objects.filter(
                    anggota=anggota,
                    jenis_simpanan=jenis
                ).aggregate(total=Sum('jumlah'))['total'] or 0
            )

            total_tarik = (
                Penarikan.objects.filter(
                    anggota=anggota,
                    jenis_simpanan=jenis
                ).aggregate(total=Sum('jumlah'))['total'] or 0
            )

            saldo = total_setor - total_tarik

            if saldo > 0:  # ✅ hanya tampilkan jika saldo > 0
                last_transaksi = HistoryTabungan.objects.filter(
                    anggota=anggota,
                    jenis_simpanan=jenis
                ).order_by('-id').first()

                data_saldo.append({
                    'jenis': jenis.get_nama_jenis_display(),
                    'jenis_id': jenis.id,
                    'saldo': saldo,
                    'last_id': last_transaksi.id if last_transaksi else None
                })

        except Exception as e:
            messages.warning(request, f"Gagal memuat saldo jenis {jenis}: {str(e)}")
            continue

    return render(request, "detail/simpanan_anggota.html", {
        'username': request.user.username,
        'role': request.user.role,
        'anggota': anggota,
        'data_saldo': data_saldo,
    })


@login_required
def detail_simpanan(request, nomor_anggota, jenis_id):
    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)
    jenis_simpanan = get_object_or_404(JenisSimpanan, id=jenis_id)

    tanggal_filter = request.GET.get("tanggal")

    try:
        history_qs = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis_simpanan
        ).order_by("-tanggal", "-id")

        if tanggal_filter:
            try:
                tanggal = datetime.datetime.strptime(tanggal_filter, "%Y-%m-%d").date()
                history_qs = history_qs.filter(tanggal=tanggal)
            except ValueError:
                messages.warning(request, "Format tanggal tidak valid, filter diabaikan")
    except Exception as e:
        messages.error(request, f"Gagal memuat riwayat transaksi: {str(e)}")
        history_qs = HistoryTabungan.objects.none()

    paginator = Paginator(history_qs, 5)
    page_history = paginator.get_page(request.GET.get("page_history", 1))

    try:
        qs = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis_simpanan
        )

        setor = qs.filter(
            jenis_transaksi='SETOR'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        tarik = qs.filter(
            jenis_transaksi='TARIK'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        koreksi = qs.filter(
            jenis_transaksi='KOREKSI'
        ).aggregate(total=Sum('jumlah'))['total'] or 0  # sudah negatif

        saldo_jenis = setor - tarik + koreksi

    except Exception as e:
        messages.error(request, f"Gagal menghitung saldo: {str(e)}")
        saldo_jenis = 0

    context = {
        "anggota": anggota,
        "jenis_simpanan": jenis_simpanan,
        "history": page_history,
        "page_obj": page_history,
        "param": "page_history",
        "saldo_jenis": saldo_jenis,
        "tanggal_filter": tanggal_filter,
    }

    return render(request, "detail/detail_simpanan.html", context)


@login_required
@transaction.atomic
def tambah_penarikan(request, nomor_anggota, jenis):
    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)  # ✅ sudah ada
    jenis_obj = get_object_or_404(JenisSimpanan, pk=jenis)              # ✅ sudah ada

    try:  # ✅ tangkap error kalkulasi saldo
        saldo = hitung_saldo(anggota, jenis_obj)
    except Exception as e:
        messages.error(request, f"Gagal menghitung saldo: {str(e)}")
        return redirect("simpanan:simpanan_anggota", nomor_anggota)

    if request.method == "POST":
        form = PenarikanForm(
            request.POST,
            anggota=anggota,
            jenis_simpanan=jenis_obj
        )

        if form.is_valid():
            try:  # ✅ tangkap error saat menyimpan penarikan
                penarikan = form.save(commit=False)
                penarikan.anggota = anggota
                penarikan.jenis_simpanan = jenis_obj
                penarikan.admin = request.user
                penarikan.save()
                messages.success(request, "Penarikan berhasil")
                return redirect("simpanan:simpanan_anggota", nomor_anggota)
            except Exception as e:
                messages.error(request, f"Gagal menyimpan penarikan: {str(e)}")
        else:
            messages.error(request, "Form tidak valid, periksa kembali isian Anda")  # ✅ tambah pesan error form

    else:
        form = PenarikanForm(
            anggota=anggota,
            jenis_simpanan=jenis_obj
        )

    return render(request, "form/penarikan_form.html", {
        "form": form,
        "anggota": anggota,
        "saldo": saldo,
        "jenis_simpanan": jenis_obj.nama_jenis,
    })


@login_required
def autocomplete_anggota(request):
    term = request.GET.get('term', '')

    try:  # ✅ tangkap error query database
        anggota_list = Anggota.objects.filter(
            nama__icontains=term,
            status='aktif'
        )[:10]

        return JsonResponse({
            "results": [
                {
                    "id": a.pk,
                    "text": f"{a.nomor_anggota} - {a.nama}"
                }
                for a in anggota_list
            ]
        })
    except Exception as e:
        return JsonResponse({"results": [], "error": f"Gagal mencari anggota: {str(e)}"}, status=500)  # ✅ sebelumnya langsung crash


@login_required
def detail_transaksi(request, id):
    transaksi = get_object_or_404(HistoryTabungan, id=id)  # ✅ sudah ada, kalau tidak ketemu → 404

    return render(request, "detail/detail_transaksi.html", {
        "transaksi": transaksi
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