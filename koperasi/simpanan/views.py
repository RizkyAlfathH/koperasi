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
        return redirect("dashboard")
    data_list = []

    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'nomor')

    anggotas = Anggota.objects.filter(status__iexact='aktif')

    if search_query:
        anggotas = anggotas.filter(
            Q(nama__icontains=search_query) |
            Q(nomor_anggota__icontains=search_query)
        )

    def get_saldo(anggota, jenis_id):
        total_setor = (
            Simpanan.objects.filter(
                anggota=anggota,
                jenis_simpanan_id=jenis_id
            ).aggregate(total=Sum('jumlah'))['total'] or 0
        )

        total_tarik = (
            Penarikan.objects.filter(
                anggota=anggota,
                jenis_simpanan_id=jenis_id
            ).aggregate(total=Sum('jumlah'))['total'] or 0
        )

        return total_setor - total_tarik

    for anggota in anggotas:
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

    # SORTING
    if sort_by == 'nama':
        data_list.sort(key=lambda x: x['nama_anggota'])
    else:
        data_list.sort(key=lambda x: x['nomor_anggota'])

    # 🔥 PAGINATION KHUSUS SIMPANAN
    paginator = Paginator(data_list, 10)
    page_simpanan = paginator.get_page(
        request.GET.get('page_simpanan', 1)
    )

    return render(request, "daftar_simpanan.html", {
        'data': page_simpanan,
        'page_obj': page_simpanan,   # wajib buat pagination.html
        'param': 'page_simpanan',    # 🔥 ini kuncinya
        'search_query': search_query,
        'sort_by': sort_by,
    })

@login_required
@transaction.atomic
def tambah_simpanan(request):
    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    if request.method == "POST":
        form = SimpananForm(request.POST)
        if form.is_valid():
            simpanan = form.save(commit=False)
            simpanan.admin = request.user
            simpanan.save()

            messages.success(request, "Simpanan berhasil ditambahkan")
            return redirect("simpanan:daftar_simpanan")
        else:
            print(form.errors)
    else:
        form = SimpananForm()

    return render(request, "form/simpanan_form.html", {"form": form})



@login_required
def cek_dana_sosial(request):
    anggota_id = request.GET.get('anggota')
    jenis_id = request.GET.get('jenis')
    tanggal_str = request.GET.get('tanggal')

    if not anggota_id or not jenis_id or not tanggal_str:
        return JsonResponse({'wajib': False})

    tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()

    sudah_bayar = Simpanan.objects.filter(
        anggota_id=anggota_id,
        jenis_simpanan_id=jenis_id,
        tanggal__month=tanggal.month,
        tanggal__year=tanggal.year
    ).exists()

    return JsonResponse({
        'wajib': not sudah_bayar
    })

@login_required
def simpanan_anggota(request, nomor_anggota):
    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)

    data_saldo = []

    for jenis in JenisSimpanan.objects.all():
        total_setor = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis,
            jenis_transaksi='SETOR'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        total_tarik = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis,
            jenis_transaksi='TARIK'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        saldo = total_setor - total_tarik

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

    # ======================
    # HISTORY (boleh difilter)
    # ======================
    history_qs = HistoryTabungan.objects.filter(
        anggota=anggota,
        jenis_simpanan=jenis_simpanan
    ).order_by("-tanggal", "-id")

    if tanggal_filter:
        try:
            tanggal = datetime.datetime.strptime(
                tanggal_filter, "%Y-%m-%d"
            ).date()
            history_qs = history_qs.filter(tanggal=tanggal)
        except ValueError:
            pass

    # 🔥 PAGINATION RIWAYAT (5 DATA)
    paginator = Paginator(history_qs, 5)
    page_history = paginator.get_page(
        request.GET.get("page_history", 1)
    )

    # ======================
    # SALDO (TIDAK BOLEH KEFILTER)
    # ======================
    saldo_qs = HistoryTabungan.objects.filter(
        anggota=anggota,
        jenis_simpanan=jenis_simpanan
    )

    total_setor = saldo_qs.filter(
        jenis_transaksi=HistoryTabungan.SETOR
    ).aggregate(total=Sum("jumlah"))["total"] or 0

    total_tarik = saldo_qs.filter(
        jenis_transaksi=HistoryTabungan.TARIK
    ).aggregate(total=Sum("jumlah"))["total"] or 0

    saldo_jenis = total_setor - total_tarik

    context = {
        "anggota": anggota,
        "jenis_simpanan": jenis_simpanan,
        "history": page_history,     # 🔥 SUDAH PAGINATION
        "page_obj": page_history,    # buat pagination.html
        "param": "page_history",     # nama query page
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

    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)
    jenis_obj = get_object_or_404(JenisSimpanan, pk=jenis)

    saldo = hitung_saldo(anggota, jenis_obj)

    if request.method == "POST":
        form = PenarikanForm(
            request.POST,
            anggota=anggota,
            jenis_simpanan=jenis_obj
        )

        if form.is_valid():
            penarikan = form.save(commit=False)
            penarikan.anggota = anggota
            penarikan.jenis_simpanan = jenis_obj
            penarikan.admin = request.user
            penarikan.save()

            messages.success(request, "Penarikan berhasil")
            return redirect("simpanan:simpanan_anggota", nomor_anggota)

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

@login_required
def detail_transaksi(request, id):
    transaksi = get_object_or_404(HistoryTabungan, id=id)

    return render(request, "detail/detail_transaksi.html", {
        "transaksi": transaksi
    })

@login_required
def download_kwitansi(request, history_id):
    trx = get_object_or_404(HistoryTabungan, id=history_id)

    anggota = trx.anggota
    tanggal = trx.tanggal
    jumlah = trx.jumlah
    jenis_simpanan = trx.jenis_simpanan

    # ================= JENIS SIMPANAN =================
    nama_simpanan = (
        jenis_simpanan.get_nama_jenis_display()
        if jenis_simpanan else "Tabungan"
    )

    # ================= SWITCH SETOR / TARIK =================
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
        # fallback (kalau suatu saat ada KOREKSI)
        judul = "BUKTI TRANSAKSI KAS"
        pihak_label = "Pihak"
        pemberi = "(...........................)"
        penerima = "(...........................)"
        filename = f"kwitansi_{anggota.nama}"

    # ================= RESPONSE =================
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'

    width, height = 25.1 * cm, 10.7 * cm
    c = canvas.Canvas(response, pagesize=(width, height))

    # ================= LOGO =================
    c.drawImage(
        "static/image/logo_koperasiK.jpeg",
        0.8 * cm, height - 2.6 * cm,
        width=2.2 * cm, height=2.2 * cm
    )

    # ================= HEADER (RATA TENGAH AREA KIRI) =================
    text_x = 3.4 * cm
    header_right_limit = width - 7.0 * cm

    shift_left = 3.5 * cm   # 🔥 UBAH ANGKA INI AJA
    header_center_x = (text_x + header_right_limit) / 2 - shift_left

    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(
        header_center_x,
        height - 0.9 * cm,
        "K P R I SMK NEGERI 11 KOTA BANDUNG"
    )

    c.setFont("Helvetica", 9)
    c.drawCentredString(
        header_center_x,
        height - 1.3 * cm,
        "( K O P A S M E N )"
    )

    c.setFont("Helvetica", 8)
    c.drawCentredString(
        header_center_x,
        height - 1.9 * cm,
        "Jl. Budi Cilember Telp. 6652442 Bandung"
    )
    c.drawCentredString(
        header_center_x,
        height - 2.2 * cm,
        "HAK BADAN HUKUM NO. : 9749/BH/KWK-10/21"
    )
    c.drawCentredString(
        header_center_x,
        height - 2.5 * cm,
        "TANGGAL : 18 NOVEMBER 1991"
    )

    # ================= JUDUL KANAN (AREA KANAN, RATA KIRI) =================

    right_block_x = width - 6.5 * cm   # 🔥 titik kiri blok kanan (atur ini)
    right_block_top = height - 0.9 * cm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(right_block_x, right_block_top, judul)

    c.setFont("Helvetica", 9)
    c.drawString(right_block_x, height - 1.5 * cm, "UNIT :")
    c.drawString(
        right_block_x,
        height - 2.0 * cm,
        "K.M. NO. ................................"
    )

    # ================= GARIS (TIDAK FULL) =================
    left_x  = 0.9 * cm     # sejajar teks header
    right_x = width - 13.0 * cm

    c.setLineWidth(2)
    c.line(left_x, height - 2.7 * cm, right_x, height - 2.7 * cm)

    c.setLineWidth(1)
    c.line(left_x, height - 2.8 * cm, right_x, height - 2.8 * cm)

    # ================= DIBERIKAN KEPADA =================
    c.setFont("Helvetica", 10)
    c.drawString(1.2 * cm, height - 3.6 * cm, f"{pihak_label} :")

    # Nama
    c.drawString(4.8 * cm, height - 3.6 * cm, anggota.nama)

    # Garis (DIHENTIKAN SEBELUM TEKS)
    line_start_x = 4.7 * cm
    line_end_x   = 12.8 * cm   # 🔥 dipendekin
    line_y       = height - 3.8 * cm
    c.line(line_start_x, line_y, line_end_x, line_y)

    # Teks SETELAH garis
    c.setFont("Helvetica", 9)
    c.drawString(
        line_end_x + 0.2 * cm,   # 🔥 mulai setelah garis
        height - 3.6 * cm,
        "(Anggota / Bukan Anggota)"
    )

    # ================= JUMLAH (3 KOTAK) =================
    c.setFont("Helvetica", 10)
    c.drawString(1.2 * cm, height - 4.5 * cm, "Jumlah    :  Rp.")

    # ================= KONFIGURASI MUDAH DIATUR =================
    box_y_top = height - 4.7 * cm   # 🔼 geser SEMUA kotak naik/turun
    box_height = 0.6 * cm           # tinggi kotak 1 & 2
    box3_height = 0.6 * cm          # tinggi kotak 3

    gap_x = 0.6 * cm                # jarak kotak 1 ke 2
    gap_y = 0.8 * cm                # 🔥 jarak kotak atas ke kotak bawah

    # ================= KOTAK 1 — ANGKA =================
    box1_x = 3.9 * cm
    box1_w = 3.8 * cm
    c.rect(box1_x, box_y_top, box1_w, box_height)

    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(
        box1_x + box1_w / 2,
        box_y_top + (box_height / 2) - 3,
        f"{int(jumlah):,}".replace(",", ".")
    )

    # ================= KOTAK 2 — TERBILANG =================
    box2_x = box1_x + box1_w + gap_x
    box2_w = 10.2 * cm
    c.rect(box2_x, box_y_top, box2_w, box_height)

    c.setFont("Helvetica", 9)
    c.drawString(
        box2_x + 0.2 * cm,
        box_y_top + (box_height / 2) - 3,
        f"{num2words(int(jumlah), lang='id').capitalize()} rupiah"
    )

    # ================= KOTAK 3 — BAWAH =================
    box3_x = 3.0 * cm
    box3_y = box_y_top - gap_y      # 🔥 INI YANG NGATUR JARAK KE BAWAH
    box3_w = 15.5 * cm
    c.rect(box3_x, box3_y, box3_w, box3_height)


    # ================= UNTUK =================
    c.setFont("Helvetica", 10)

    text_y = height - 6.0 * cm
    line_gap = 0.1 * cm   # 🔥 jarak titik ke teks

    c.drawString(1.2 * cm, text_y, "Untuk :")

    # Titik-titik DI BAWAH teks
    c.setDash(1, 2)
    c.line(3.0 * cm, text_y - line_gap, 18.5 * cm, text_y - line_gap)
    c.line(3.0 * cm, text_y - line_gap - 0.6 * cm,
        18.5 * cm, text_y - line_gap - 0.5 * cm)
    c.setDash()

    # ================= TANGGAL =================
    c.setFont("Helvetica", 9)
    c.drawRightString(
        width - 1.2 * cm, 4.8 * cm,
        f"Bandung, {tanggal.strftime('%d %B %Y')}"
    )

    # ================= TANDA TANGAN =================
    c.drawCentredString(2.2 * cm, 2.8 * cm, pemberi)
    c.drawCentredString(2.2 * cm, 2.5 * cm, "Bendahara")

    c.drawCentredString(width - 3.2 * cm, 2.8 * cm, penerima)
    c.drawCentredString(width - 3.2 * cm, 2.5 * cm, "Penerima")

    # ================= TABEL PEMBUKUAN =================
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

        # FONT
        ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONT", (0,1), (0,-1), "Helvetica-Bold"),

        # ALIGNMENT
        ("ALIGN", (1,0), (-1,0), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

        # 🔥 INI PENTING: PARAF DIGABUNG KE BAWAH
        ("SPAN", (4,1), (4,2)),
    ]))

    table.wrapOn(c, width, height)
    table.drawOn(c, 0.9 * cm, 0.6 * cm)

    c.save()
    return response