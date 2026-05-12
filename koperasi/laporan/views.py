from django.shortcuts import render
from django.http import HttpResponse
from django.utils.timezone import now
from django.db.models import Sum, Q, Count
from django.core.paginator import Paginator
from datetime import datetime, time, date
import calendar
import io
import xlsxwriter

# reportlab – untuk export PDF
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable
)

from anggota.models import Anggota
from simpanan.models import Simpanan
from pinjaman.models import Pinjaman, Angsuran


# ──────────────────────────────────────────────────────────────
# LAPORAN KEUANGAN (existing, tidak diubah)
# ──────────────────────────────────────────────────────────────

def laporan(request):
    anggota_qs = Anggota.objects.order_by("nama")

    bulan = int(request.GET.get("bulan", now().month))
    tahun_bulan = int(request.GET.get("tahun", now().year))
    tahun_tahunan = int(request.GET.get("tahun_tahunan", now().year))

    per_page_bulan = int(request.GET.get("per_page_bulan", 10))
    per_page_tahun = int(request.GET.get("per_page_tahun", 10))

    bulan_choices = [
        (1, "Januari"), (2, "Februari"), (3, "Maret"),
        (4, "April"), (5, "Mei"), (6, "Juni"),
        (7, "Juli"), (8, "Agustus"), (9, "September"),
        (10, "Oktober"), (11, "November"), (12, "Desember"),
    ]

    tahun_range = range(2020, now().year + 1)

    last_day = calendar.monthrange(tahun_bulan, bulan)[1]
    akhir_bulan = datetime.combine(
        datetime(tahun_bulan, bulan, last_day),
        time(23, 59, 59)
    )

    laporan_bulanan = generate_laporan(anggota_qs, akhir_bulan)
    paginator_bulan = Paginator(laporan_bulanan, per_page_bulan)
    page_bulan = request.GET.get("page_bulan")
    laporan_bulanan = paginator_bulan.get_page(page_bulan)

    akhir_tahun = datetime.combine(
        datetime(tahun_tahunan, 12, 31),
        time(23, 59, 59)
    )

    laporan_tahunan = generate_laporan(anggota_qs, akhir_tahun)
    paginator_tahun = Paginator(laporan_tahunan, per_page_tahun)
    page_tahun = request.GET.get("page_tahun")
    laporan_tahunan = paginator_tahun.get_page(page_tahun)

    return render(request, "laporan.html", {
        "bulan": bulan,
        "tahun_bulan": tahun_bulan,
        "tahun_tahunan": tahun_tahunan,
        "bulan_choices": bulan_choices,
        "tahun_range": tahun_range,
        "laporan_bulanan": laporan_bulanan,
        "laporan_tahunan": laporan_tahunan,
        "akhir_bulan": akhir_bulan,
        "akhir_tahun": akhir_tahun,
        "per_page_bulan": per_page_bulan,
        "per_page_tahun": per_page_tahun,
    })


def generate_laporan(anggota_qs, akhir=None):
    laporan = []

    for idx, anggota in enumerate(anggota_qs, start=1):
        simpanan_filter = {"anggota": anggota}
        if akhir:
            simpanan_filter["tanggal__lte"] = akhir

        pokok = Simpanan.objects.filter(
            **simpanan_filter,
            jenis_simpanan__nama_jenis="POKOK"
        ).aggregate(total=Sum("jumlah"))["total"] or 0

        wajib = Simpanan.objects.filter(
            **simpanan_filter,
            jenis_simpanan__nama_jenis="WAJIB"
        ).aggregate(total=Sum("jumlah"))["total"] or 0

        sukarela = Simpanan.objects.filter(
            **simpanan_filter,
            jenis_simpanan__nama_jenis="SUKARELA"
        ).aggregate(total=Sum("jumlah"))["total"] or 0

        dana_sosial = Simpanan.objects.filter(
            **simpanan_filter,
        ).aggregate(total=Sum("dana_sosial"))["total"] or 0

        total_simpanan = pokok + wajib + sukarela + dana_sosial

        total_reguler = total_khusus = total_barang = 0

        pinjaman_qs = Pinjaman.objects.filter(
            nomor_anggota=anggota,
            tanggal_meminjam__lte=akhir if akhir else now()
        )

        for jenis in ["Reguler", "Khusus", "Barang"]:
            pinjaman = pinjaman_qs.filter(
                id_jenis_pinjaman__nama_jenis=jenis
            ).order_by("-tanggal_meminjam").first()

            if not pinjaman:
                continue

            cicilan = Angsuran.objects.filter(
                id_pinjaman=pinjaman,
                tanggal_bayar__lte=akhir if akhir else now()
            ).count()

            angsuran_pokok = pinjaman.angsuran_per_bulan or 0
            sisa_pinjaman = pinjaman.jumlah_pinjaman - (cicilan * angsuran_pokok)

            if sisa_pinjaman <= 0:
                continue

            if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
                jasa = sisa_pinjaman * (pinjaman.jasa_persen / 100)
            else:
                jasa = pinjaman.jumlah_pinjaman * (pinjaman.jasa_persen / 100)

            total_sisa = sisa_pinjaman + jasa

            if jenis == "Reguler":
                total_reguler += total_sisa
            elif jenis == "Khusus":
                total_khusus += total_sisa
            elif jenis == "Barang":
                total_barang += total_sisa

        laporan.append({
            "no": anggota.nomor_anggota,
            "nama": anggota.nama,
            "simpanan": {
                "pokok": pokok,
                "wajib": wajib,
                "sukarela": sukarela,
                "dana_sosial": dana_sosial,
                "total": total_simpanan
            },
            "pinjaman": {
                "reguler": total_reguler,
                "khusus": total_khusus,
                "barang": total_barang,
                "total": total_reguler + total_khusus + total_barang
            }
        })

    return laporan


def export_laporan(request):
    periode = request.GET.get("periode", "bulan")
    bulan = int(request.GET.get("bulan", now().month))
    tahun = int(request.GET.get("tahun", now().year))

    anggota_qs = Anggota.objects.order_by("nama")

    if periode == "tahun":
        akhir = datetime.combine(datetime(tahun, 12, 31), time(23, 59, 59))
        judul_periode = f"31 DESEMBER {tahun}"
        nama_file = f"Laporan Tahun {tahun}.xlsx"
    else:
        last_day = calendar.monthrange(tahun, bulan)[1]
        akhir = datetime.combine(datetime(tahun, bulan, last_day), time(23, 59, 59))

        nama_bulan = [
            "", "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI",
            "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"
        ][bulan]

        judul_periode = f"{last_day} {nama_bulan} {tahun}"
        nama_file = f"Laporan {nama_bulan} {tahun}.xlsx"

    laporan = generate_laporan(anggota_qs, akhir)

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    bold_center = workbook.add_format({'bold': True, 'align': 'center'})
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
    border_fmt = workbook.add_format({'border': 1})
    money_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0'})

    ws1 = workbook.add_worksheet("Simpanan")
    ws1.merge_range("A1:F1", "KOPASMEN", bold_center)
    ws1.merge_range("A2:F2", "DAFTAR SIMPANAN POKOK, WAJIB DAN SUKARELA", bold_center)
    ws1.merge_range("A3:F3", f"PER {judul_periode}", bold_center)

    for col, h in enumerate(["NO", "NAMA ANGGOTA", "POKOK", "WAJIB", "SUKARELA", "TOTAL"]):
        ws1.write(4, col, h, header_fmt)

    for r, row in enumerate(laporan, start=5):
        s = row["simpanan"]
        ws1.write(r, 0, row["no"], border_fmt)
        ws1.write(r, 1, row["nama"], border_fmt)
        ws1.write(r, 2, s["pokok"], money_fmt)
        ws1.write(r, 3, s["wajib"], money_fmt)
        ws1.write(r, 4, s["sukarela"], money_fmt)
        ws1.write(r, 5, s["total"], money_fmt)

    ws1.set_column("A:A", 5)
    ws1.set_column("B:B", 30)
    ws1.set_column("C:F", 15)

    ws2 = workbook.add_worksheet("Pinjaman")
    ws2.merge_range("A1:F1", "KOPASMEN", bold_center)
    ws2.merge_range("A2:F2", "DAFTAR SALDO PIUTANG", bold_center)
    ws2.merge_range("A3:F3", f"PER {judul_periode}", bold_center)

    for col, h in enumerate(["NO", "NAMA ANGGOTA", "REGULER", "KHUSUS", "BARANG", "TOTAL"]):
        ws2.write(4, col, h, header_fmt)

    for r, row in enumerate(laporan, start=5):
        p = row["pinjaman"]
        ws2.write(r, 0, row["no"], border_fmt)
        ws2.write(r, 1, row["nama"], border_fmt)
        ws2.write(r, 2, p["reguler"], money_fmt)
        ws2.write(r, 3, p["khusus"], money_fmt)
        ws2.write(r, 4, p["barang"], money_fmt)
        ws2.write(r, 5, p["total"], money_fmt)

    ws2.set_column("A:A", 5)
    ws2.set_column("B:B", 30)
    ws2.set_column("C:F", 15)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{nama_file}"'
    return response


# ──────────────────────────────────────────────────────────────
# LAPORAN KEANGGOTAAN (new)
# ──────────────────────────────────────────────────────────────

NAMA_BULAN_LIST = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

NAMA_BULAN_UPPER = [b.upper() for b in NAMA_BULAN_LIST]


def laporan_keanggotaan(request):
    """
    View laporan keanggotaan untuk sekretaris.
    Menampilkan:
    - Rekap statistik (aktif, nonaktif, total, laki-laki, perempuan)
    - Anggota masuk per bulan yang dipilih
    - Anggota nonaktif/keluar per bulan yang dipilih
    - Tabel semua anggota (bisa filter status & cari nama)
    """

    tahun_range = range(2020, now().year + 1)
    bulan_choices = [(i, NAMA_BULAN_LIST[i]) for i in range(1, 13)]

    # ── Parameter GET ────────────────────────────────────────
    bulan = int(request.GET.get("bulan", now().month))
    tahun = int(request.GET.get("tahun", now().year))
    status_filter = request.GET.get("status", "semua")   # aktif / nonaktif / semua
    cari = request.GET.get("cari", "").strip()
    per_page = int(request.GET.get("per_page", 10))

    # ── Tanggal awal & akhir bulan ───────────────────────────
    last_day = calendar.monthrange(tahun, bulan)[1]
    awal_bulan_dt = date(tahun, bulan, 1)
    akhir_bulan_dt = date(tahun, bulan, last_day)

    # ── Statistik ringkasan (sampai akhir bulan dipilih) ─────
    semua_anggota = Anggota.objects.all()

    total_aktif = semua_anggota.filter(
        Q(tanggal_daftar__lte=akhir_bulan_dt) &
        (Q(status="aktif") | Q(tanggal_nonaktif__gt=akhir_bulan_dt))
    ).count()

    total_nonaktif = semua_anggota.filter(
        status="nonaktif",
        tanggal_nonaktif__lte=akhir_bulan_dt
    ).count()

    total_anggota = semua_anggota.filter(tanggal_daftar__lte=akhir_bulan_dt).count()

    total_laki = semua_anggota.filter(
        jenis_kelamin="Laki-laki",
        tanggal_daftar__lte=akhir_bulan_dt
    ).count()

    total_perempuan = semua_anggota.filter(
        jenis_kelamin="Perempuan",
        tanggal_daftar__lte=akhir_bulan_dt
    ).count()

    # ── Anggota masuk bulan ini ──────────────────────────────
    anggota_masuk = semua_anggota.filter(
        tanggal_daftar__gte=awal_bulan_dt,
        tanggal_daftar__lte=akhir_bulan_dt
    ).order_by("tanggal_daftar")

    # ── Anggota keluar/nonaktif bulan ini ────────────────────
    anggota_keluar = semua_anggota.filter(
        status="nonaktif",
        tanggal_nonaktif__gte=awal_bulan_dt,
        tanggal_nonaktif__lte=akhir_bulan_dt
    ).order_by("tanggal_nonaktif")

    # ── Tabel semua anggota (dengan filter & search) ─────────
    tabel_qs = semua_anggota.filter(tanggal_daftar__lte=akhir_bulan_dt)

    if status_filter == "aktif":
        tabel_qs = tabel_qs.filter(
            Q(status="aktif") | Q(tanggal_nonaktif__gt=akhir_bulan_dt)
        )
    elif status_filter == "nonaktif":
        tabel_qs = tabel_qs.filter(
            status="nonaktif",
            tanggal_nonaktif__lte=akhir_bulan_dt
        )

    if cari:
        tabel_qs = tabel_qs.filter(
            Q(nama__icontains=cari) | Q(nomor_anggota__icontains=cari)
        )

    tabel_qs = tabel_qs.order_by("nama")

    paginator = Paginator(tabel_qs, per_page)
    page_num = request.GET.get("page")
    tabel_anggota = paginator.get_page(page_num)

    # ── Rekap per bulan dalam setahun (untuk grafik/tabel tren) ──
    rekap_bulanan = []
    for b in range(1, 13):
        ld = calendar.monthrange(tahun, b)[1]
        awal = date(tahun, b, 1)
        akhir = date(tahun, b, ld)

        masuk_bln = semua_anggota.filter(
            tanggal_daftar__gte=awal,
            tanggal_daftar__lte=akhir
        ).count()

        keluar_bln = semua_anggota.filter(
            status="nonaktif",
            tanggal_nonaktif__gte=awal,
            tanggal_nonaktif__lte=akhir
        ).count()

        aktif_bln = semua_anggota.filter(
            Q(tanggal_daftar__lte=akhir) &
            (Q(status="aktif") | Q(tanggal_nonaktif__gt=akhir))
        ).count()

        rekap_bulanan.append({
            "bulan": NAMA_BULAN_LIST[b],
            "masuk": masuk_bln,
            "keluar": keluar_bln,
            "aktif": aktif_bln,
        })

    return render(request, "laporan_keanggotaan.html", {
        "bulan": bulan,
        "tahun": tahun,
        "bulan_choices": bulan_choices,
        "tahun_range": tahun_range,
        "nama_bulan": NAMA_BULAN_LIST[bulan],
        "akhir_bulan_dt": akhir_bulan_dt,

        # statistik
        "total_aktif": total_aktif,
        "total_nonaktif": total_nonaktif,
        "total_anggota": total_anggota,
        "total_laki": total_laki,
        "total_perempuan": total_perempuan,

        # tabel masuk / keluar bulan ini
        "anggota_masuk": anggota_masuk,
        "anggota_keluar": anggota_keluar,

        # tabel utama (semua anggota)
        "tabel_anggota": tabel_anggota,
        "status_filter": status_filter,
        "cari": cari,
        "per_page": per_page,

        # rekap setahun
        "rekap_bulanan": rekap_bulanan,
    })


def export_laporan_keanggotaan(request):
    """Export laporan keanggotaan ke Excel."""

    bulan = int(request.GET.get("bulan", now().month))
    tahun = int(request.GET.get("tahun", now().year))

    last_day = calendar.monthrange(tahun, bulan)[1]
    awal_bulan_dt = date(tahun, bulan, 1)
    akhir_bulan_dt = date(tahun, bulan, last_day)

    nama_bulan_str = NAMA_BULAN_UPPER[bulan]
    judul_periode = f"{last_day} {nama_bulan_str} {tahun}"
    nama_file = f"Laporan Keanggotaan {nama_bulan_str} {tahun}.xlsx"

    semua_anggota = Anggota.objects.filter(
        tanggal_daftar__lte=akhir_bulan_dt
    ).order_by("nama")

    anggota_masuk = Anggota.objects.filter(
        tanggal_daftar__gte=awal_bulan_dt,
        tanggal_daftar__lte=akhir_bulan_dt
    ).order_by("tanggal_daftar")

    anggota_keluar = Anggota.objects.filter(
        status="nonaktif",
        tanggal_nonaktif__gte=awal_bulan_dt,
        tanggal_nonaktif__lte=akhir_bulan_dt
    ).order_by("tanggal_nonaktif")

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # ── Format ───────────────────────────────────────────────
    def fmt(**kwargs):
        base = {'font_name': 'Calibri', 'font_size': 11}
        base.update(kwargs)
        return workbook.add_format(base)

    title_fmt   = fmt(bold=True, align='center', font_size=13)
    sub_fmt     = fmt(bold=True, align='center', font_size=11)
    header_fmt  = fmt(bold=True, border=1, align='center',
                      bg_color='#FFD700', font_color='#291B18')
    border_fmt  = fmt(border=1)
    center_fmt  = fmt(border=1, align='center')
    date_fmt    = fmt(border=1, num_format='DD/MM/YYYY')
    stat_label  = fmt(bold=True, bg_color='#FFF8DC', border=1)
    stat_val    = fmt(bold=True, border=1, align='center',
                      bg_color='#FFFDE7', font_size=12)

    # ══════════════════════════════════════════════════════════
    # Sheet 1: Rekap Statistik
    # ══════════════════════════════════════════════════════════
    ws_rekap = workbook.add_worksheet("Rekap Statistik")
    ws_rekap.merge_range("A1:D1", "KOPASMEN", title_fmt)
    ws_rekap.merge_range("A2:D2", "LAPORAN KEANGGOTAAN", sub_fmt)
    ws_rekap.merge_range("A3:D3", f"PER {judul_periode}", sub_fmt)

    ws_rekap.write(4, 0, "KETERANGAN", header_fmt)
    ws_rekap.write(4, 1, "JUMLAH", header_fmt)
    ws_rekap.write(4, 2, "KETERANGAN", header_fmt)
    ws_rekap.write(4, 3, "JUMLAH", header_fmt)

    total_aktif = Anggota.objects.filter(
        Q(tanggal_daftar__lte=akhir_bulan_dt) &
        (Q(status="aktif") | Q(tanggal_nonaktif__gt=akhir_bulan_dt))
    ).count()

    total_nonaktif = Anggota.objects.filter(
        status="nonaktif",
        tanggal_nonaktif__lte=akhir_bulan_dt
    ).count()

    total_laki = semua_anggota.filter(jenis_kelamin="Laki-laki").count()
    total_perempuan = semua_anggota.filter(jenis_kelamin="Perempuan").count()

    stats = [
        ("Total Anggota", semua_anggota.count(), "Anggota Masuk Bulan Ini", anggota_masuk.count()),
        ("Anggota Aktif", total_aktif, "Anggota Keluar Bulan Ini", anggota_keluar.count()),
        ("Anggota Nonaktif", total_nonaktif, "", ""),
        ("Laki-laki", total_laki, "Perempuan", total_perempuan),
    ]

    for r, (l1, v1, l2, v2) in enumerate(stats, start=5):
        ws_rekap.write(r, 0, l1, stat_label)
        ws_rekap.write(r, 1, v1, stat_val)
        ws_rekap.write(r, 2, l2, stat_label)
        ws_rekap.write(r, 3, v2, stat_val)

    ws_rekap.set_column("A:A", 25)
    ws_rekap.set_column("B:B", 12)
    ws_rekap.set_column("C:C", 25)
    ws_rekap.set_column("D:D", 12)

    # ══════════════════════════════════════════════════════════
    # Sheet 2: Daftar Semua Anggota
    # ══════════════════════════════════════════════════════════
    ws_all = workbook.add_worksheet("Daftar Anggota")
    ws_all.merge_range("A1:H1", "KOPASMEN", title_fmt)
    ws_all.merge_range("A2:H2", "DAFTAR ANGGOTA", sub_fmt)
    ws_all.merge_range("A3:H3", f"PER {judul_periode}", sub_fmt)

    headers = ["NO", "NOMOR ANGGOTA", "NAMA", "JENIS KELAMIN",
               "PEKERJAAN", "NO. TELP", "TANGGAL DAFTAR", "STATUS"]
    for col, h in enumerate(headers):
        ws_all.write(4, col, h, header_fmt)

    for r, ang in enumerate(semua_anggota, start=5):
        status_str = "Aktif" if (
            ang.status == "aktif" or
            (ang.tanggal_nonaktif and ang.tanggal_nonaktif > akhir_bulan_dt)
        ) else "Nonaktif"

        ws_all.write(r, 0, r - 4, center_fmt)
        ws_all.write(r, 1, ang.nomor_anggota, center_fmt)
        ws_all.write(r, 2, ang.nama, border_fmt)
        ws_all.write(r, 3, ang.jenis_kelamin or "-", center_fmt)
        ws_all.write(r, 4, ang.pekerjaan or "-", border_fmt)
        ws_all.write(r, 5, ang.no_telp or "-", center_fmt)
        if ang.tanggal_daftar:
            ws_all.write_datetime(r, 6,
                datetime.combine(ang.tanggal_daftar, time(0, 0)), date_fmt)
        else:
            ws_all.write(r, 6, "-", center_fmt)
        ws_all.write(r, 7, status_str, center_fmt)

    ws_all.set_column("A:A", 5)
    ws_all.set_column("B:B", 18)
    ws_all.set_column("C:C", 30)
    ws_all.set_column("D:D", 15)
    ws_all.set_column("E:E", 20)
    ws_all.set_column("F:F", 18)
    ws_all.set_column("G:G", 16)
    ws_all.set_column("H:H", 12)

    # ══════════════════════════════════════════════════════════
    # Sheet 3: Anggota Masuk
    # ══════════════════════════════════════════════════════════
    ws_masuk = workbook.add_worksheet("Anggota Masuk")
    ws_masuk.merge_range("A1:F1", "KOPASMEN", title_fmt)
    ws_masuk.merge_range("A2:F2", f"ANGGOTA MASUK – {NAMA_BULAN_UPPER[bulan]} {tahun}", sub_fmt)

    for col, h in enumerate(["NO", "NOMOR ANGGOTA", "NAMA", "JENIS KELAMIN",
                              "PEKERJAAN", "TANGGAL DAFTAR"]):
        ws_masuk.write(3, col, h, header_fmt)

    for r, ang in enumerate(anggota_masuk, start=4):
        ws_masuk.write(r, 0, r - 3, center_fmt)
        ws_masuk.write(r, 1, ang.nomor_anggota, center_fmt)
        ws_masuk.write(r, 2, ang.nama, border_fmt)
        ws_masuk.write(r, 3, ang.jenis_kelamin or "-", center_fmt)
        ws_masuk.write(r, 4, ang.pekerjaan or "-", border_fmt)
        if ang.tanggal_daftar:
            ws_masuk.write_datetime(r, 5,
                datetime.combine(ang.tanggal_daftar, time(0, 0)), date_fmt)
        else:
            ws_masuk.write(r, 5, "-", center_fmt)

    ws_masuk.set_column("A:A", 5)
    ws_masuk.set_column("B:B", 18)
    ws_masuk.set_column("C:C", 30)
    ws_masuk.set_column("D:D", 15)
    ws_masuk.set_column("E:E", 20)
    ws_masuk.set_column("F:F", 16)

    # ══════════════════════════════════════════════════════════
    # Sheet 4: Anggota Keluar
    # ══════════════════════════════════════════════════════════
    ws_keluar = workbook.add_worksheet("Anggota Keluar")
    ws_keluar.merge_range("A1:G1", "KOPASMEN", title_fmt)
    ws_keluar.merge_range("A2:G2", f"ANGGOTA KELUAR – {NAMA_BULAN_UPPER[bulan]} {tahun}", sub_fmt)

    for col, h in enumerate(["NO", "NOMOR ANGGOTA", "NAMA", "JENIS KELAMIN",
                              "TANGGAL DAFTAR", "TANGGAL NONAKTIF", "ALASAN"]):
        ws_keluar.write(3, col, h, header_fmt)

    for r, ang in enumerate(anggota_keluar, start=4):
        ws_keluar.write(r, 0, r - 3, center_fmt)
        ws_keluar.write(r, 1, ang.nomor_anggota, center_fmt)
        ws_keluar.write(r, 2, ang.nama, border_fmt)
        ws_keluar.write(r, 3, ang.jenis_kelamin or "-", center_fmt)
        if ang.tanggal_daftar:
            ws_keluar.write_datetime(r, 4,
                datetime.combine(ang.tanggal_daftar, time(0, 0)), date_fmt)
        else:
            ws_keluar.write(r, 4, "-", center_fmt)
        if ang.tanggal_nonaktif:
            ws_keluar.write_datetime(r, 5,
                datetime.combine(ang.tanggal_nonaktif, time(0, 0)), date_fmt)
        else:
            ws_keluar.write(r, 5, "-", center_fmt)
        ws_keluar.write(r, 6, ang.alasan_nonaktif or "-", border_fmt)

    ws_keluar.set_column("A:A", 5)
    ws_keluar.set_column("B:B", 18)
    ws_keluar.set_column("C:C", 30)
    ws_keluar.set_column("D:D", 15)
    ws_keluar.set_column("E:F", 18)
    ws_keluar.set_column("G:G", 35)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{nama_file}"'
    return response

# ──────────────────────────────────────────────────────────────
# EXPORT PDF KEANGGOTAAN
# ──────────────────────────────────────────────────────────────

# Warna brand KOPASMEN
GOLD    = colors.HexColor("#FFD700")
DARK    = colors.HexColor("#291B18")
WHITE   = colors.white
LIGHT_Y = colors.HexColor("#FFFDE7")
GREEN   = colors.HexColor("#16a34a")
RED     = colors.HexColor("#dc2626")
GREY    = colors.HexColor("#6b7280")
LGREY   = colors.HexColor("#f3f4f6")


def _pdf_styles():
    """Kumpulan ParagraphStyle yang dipakai di PDF."""
    s = getSampleStyleSheet()

    judul = ParagraphStyle(
        "judul",
        fontName="Helvetica-Bold",
        fontSize=14,
        alignment=TA_CENTER,
        textColor=DARK,
        spaceAfter=2,
    )
    sub = ParagraphStyle(
        "sub",
        fontName="Helvetica",
        fontSize=10,
        alignment=TA_CENTER,
        textColor=GREY,
        spaceAfter=2,
    )
    section = ParagraphStyle(
        "section",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=DARK,
        spaceBefore=14,
        spaceAfter=6,
    )
    kecil = ParagraphStyle(
        "kecil",
        fontName="Helvetica",
        fontSize=8,
        textColor=GREY,
        alignment=TA_CENTER,
    )
    return judul, sub, section, kecil


def _tbl_style_header(extra=None):
    """TableStyle dasar untuk tabel dengan header kuning."""
    base = [
        # Header row
        ("BACKGROUND",  (0, 0), (-1, 0), GOLD),
        ("TEXTCOLOR",   (0, 0), (-1, 0), DARK),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 8),
        ("ALIGN",       (0, 0), (-1, 0), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        # Data rows
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 7.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGREY]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if extra:
        base.extend(extra)
    return TableStyle(base)


def export_laporan_keanggotaan_pdf(request):
    """Export laporan keanggotaan ke PDF (landscape A4)."""

    bulan = int(request.GET.get("bulan", now().month))
    tahun = int(request.GET.get("tahun", now().year))

    last_day  = calendar.monthrange(tahun, bulan)[1]
    awal_dt   = date(tahun, bulan, 1)
    akhir_dt  = date(tahun, bulan, last_day)

    nama_bln_str  = NAMA_BULAN_LIST[bulan].upper()
    judul_periode = f"{last_day} {nama_bln_str} {tahun}"
    nama_file     = f"Laporan Keanggotaan {nama_bln_str} {tahun}.pdf"

    semua = Anggota.objects.filter(tanggal_daftar__lte=akhir_dt).order_by("nama")

    total_aktif = Anggota.objects.filter(
        Q(tanggal_daftar__lte=akhir_dt) &
        (Q(status="aktif") | Q(tanggal_nonaktif__gt=akhir_dt))
    ).count()

    total_nonaktif = Anggota.objects.filter(
        status="nonaktif",
        tanggal_nonaktif__lte=akhir_dt
    ).count()

    total_laki      = semua.filter(jenis_kelamin="Laki-laki").count()
    total_perempuan = semua.filter(jenis_kelamin="Perempuan").count()

    anggota_masuk  = Anggota.objects.filter(
        tanggal_daftar__gte=awal_dt,
        tanggal_daftar__lte=akhir_dt
    ).order_by("tanggal_daftar")

    anggota_keluar = Anggota.objects.filter(
        status="nonaktif",
        tanggal_nonaktif__gte=awal_dt,
        tanggal_nonaktif__lte=akhir_dt
    ).order_by("tanggal_nonaktif")

    # Rekap 12 bulan
    rekap = []
    for b in range(1, 13):
        ld   = calendar.monthrange(tahun, b)[1]
        aw   = date(tahun, b, 1)
        ak   = date(tahun, b, ld)
        masuk_n  = Anggota.objects.filter(tanggal_daftar__gte=aw, tanggal_daftar__lte=ak).count()
        keluar_n = Anggota.objects.filter(
            status="nonaktif", tanggal_nonaktif__gte=aw, tanggal_nonaktif__lte=ak).count()
        aktif_n  = Anggota.objects.filter(
            Q(tanggal_daftar__lte=ak) &
            (Q(status="aktif") | Q(tanggal_nonaktif__gt=ak))
        ).count()
        rekap.append((NAMA_BULAN_LIST[b], masuk_n, keluar_n, aktif_n))

    # ── Build PDF ──────────────────────────────────────────────
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.5 * cm,
    )

    judul_sty, sub_sty, section_sty, kecil_sty = _pdf_styles()
    story = []

    # ── Header dokumen ─────────────────────────────────────────
    story.append(Paragraph("KOPASMEN", judul_sty))
    story.append(Paragraph("LAPORAN KEANGGOTAAN", judul_sty))
    story.append(Paragraph(f"PER {judul_periode}", sub_sty))
    story.append(HRFlowable(width="100%", thickness=1.5,
                            color=GOLD, spaceAfter=10))

    # ── 1. Ringkasan Statistik ─────────────────────────────────
    story.append(Paragraph("1. Ringkasan Statistik", section_sty))

    stat_data = [
        ["Keterangan", "Jumlah", "Keterangan", "Jumlah"],
        ["Total Anggota Terdaftar", str(semua.count()),
         f"Anggota Masuk ({NAMA_BULAN_LIST[bulan]} {tahun})", str(anggota_masuk.count())],
        ["Anggota Aktif", str(total_aktif),
         f"Anggota Keluar ({NAMA_BULAN_LIST[bulan]} {tahun})", str(anggota_keluar.count())],
        ["Anggota Nonaktif", str(total_nonaktif), "", ""],
        ["Laki-laki", str(total_laki), "Perempuan", str(total_perempuan)],
    ]

    col_w = [9 * cm, 3 * cm, 9 * cm, 3 * cm]
    tbl_stat = Table(stat_data, colWidths=col_w, repeatRows=1)
    tbl_stat.setStyle(_tbl_style_header([
        ("ALIGN",      (1, 1), (1, -1), "CENTER"),
        ("ALIGN",      (3, 1), (3, -1), "CENTER"),
        ("FONTNAME",   (1, 1), (1, -1), "Helvetica-Bold"),
        ("FONTNAME",   (3, 1), (3, -1), "Helvetica-Bold"),
        ("FONTSIZE",   (1, 1), (1, -1), 9),
        ("FONTSIZE",   (3, 1), (3, -1), 9),
        ("SPAN",       (0, 4), (0, 4)),
        ("SPAN",       (2, 3), (3, 3)),
    ]))
    story.append(tbl_stat)

    # ── 2. Rekap Bulanan ───────────────────────────────────────
    story.append(Paragraph(f"2. Rekap Pergerakan Anggota Tahun {tahun}", section_sty))

    rek_data = [["Bulan", "Masuk", "Keluar", "Total Aktif (s.d. akhir bulan)"]]
    for i, (nm, mk, kl, ak) in enumerate(rekap, start=1):
        row = [nm, str(mk) if mk else "-", str(kl) if kl else "-", str(ak)]
        rek_data.append(row)

    # Highlight baris bulan yang dipilih
    highlight_extras = []
    highlight_row = bulan  # baris ke-N (1-indexed header di baris 0)
    highlight_extras += [
        ("BACKGROUND", (0, highlight_row), (-1, highlight_row), LIGHT_Y),
        ("FONTNAME",   (0, highlight_row), (-1, highlight_row), "Helvetica-Bold"),
        ("TEXTCOLOR",  (1, highlight_row), (1, highlight_row),  GREEN),
        ("TEXTCOLOR",  (2, highlight_row), (2, highlight_row),  RED),
    ]

    rek_col = [5 * cm, 3 * cm, 3 * cm, 6 * cm]
    tbl_rek = Table(rek_data, colWidths=rek_col, repeatRows=1)
    tbl_rek.setStyle(_tbl_style_header([
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ] + highlight_extras))
    story.append(tbl_rek)

    # ── 3. Anggota Masuk ──────────────────────────────────────
    story.append(Paragraph(
        f"3. Anggota Masuk – {NAMA_BULAN_LIST[bulan]} {tahun} "
        f"({anggota_masuk.count()} orang)",
        section_sty
    ))

    if anggota_masuk.exists():
        masuk_data = [["No", "Nomor Anggota", "Nama", "Jenis Kelamin",
                        "Pekerjaan", "Tanggal Daftar"]]
        for i, ang in enumerate(anggota_masuk, start=1):
            masuk_data.append([
                str(i),
                ang.nomor_anggota,
                ang.nama,
                ang.jenis_kelamin or "-",
                ang.pekerjaan or "-",
                ang.tanggal_daftar.strftime("%d/%m/%Y") if ang.tanggal_daftar else "-",
            ])
        tbl_masuk = Table(masuk_data,
                          colWidths=[1*cm, 4*cm, 7*cm, 3.5*cm, 5*cm, 3.5*cm],
                          repeatRows=1)
        tbl_masuk.setStyle(_tbl_style_header([
            ("ALIGN",    (0, 1), (0, -1), "CENTER"),
            ("ALIGN",    (5, 1), (5, -1), "CENTER"),
            ("TEXTCOLOR", (0, 1), (-1, -1), GREEN),
        ]))
        # Kembalikan warna teks data ke hitam, hanya No yang hijau
        tbl_masuk.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), GOLD),
            ("TEXTCOLOR",   (0, 0), (-1, 0), DARK),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 8),
            ("ALIGN",       (0, 0), (-1, 0), "CENTER"),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 1), (-1, -1), 7.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGREY]),
            ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
            ("TOPPADDING",  (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("ALIGN",       (0, 1), (0, -1), "CENTER"),
            ("ALIGN",       (5, 1), (5, -1), "CENTER"),
        ]))
        story.append(tbl_masuk)
    else:
        story.append(Paragraph(
            f"Tidak ada anggota baru masuk pada {NAMA_BULAN_LIST[bulan]} {tahun}.",
            kecil_sty
        ))

    # ── 4. Anggota Keluar ─────────────────────────────────────
    story.append(Paragraph(
        f"4. Anggota Keluar – {NAMA_BULAN_LIST[bulan]} {tahun} "
        f"({anggota_keluar.count()} orang)",
        section_sty
    ))

    if anggota_keluar.exists():
        keluar_data = [["No", "Nomor Anggota", "Nama", "Jenis Kelamin",
                         "Tgl Daftar", "Tgl Nonaktif", "Alasan"]]
        for i, ang in enumerate(anggota_keluar, start=1):
            keluar_data.append([
                str(i),
                ang.nomor_anggota,
                ang.nama,
                ang.jenis_kelamin or "-",
                ang.tanggal_daftar.strftime("%d/%m/%Y") if ang.tanggal_daftar else "-",
                ang.tanggal_nonaktif.strftime("%d/%m/%Y") if ang.tanggal_nonaktif else "-",
                ang.alasan_nonaktif or "-",
            ])
        tbl_keluar = Table(keluar_data,
                           colWidths=[1*cm, 3.5*cm, 6*cm, 3*cm, 3*cm, 3*cm, 4.5*cm],
                           repeatRows=1)
        tbl_keluar.setStyle(_tbl_style_header([
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("ALIGN", (4, 1), (5, -1), "CENTER"),
        ]))
        story.append(tbl_keluar)
    else:
        story.append(Paragraph(
            f"Tidak ada anggota keluar pada {NAMA_BULAN_LIST[bulan]} {tahun}.",
            kecil_sty
        ))

    # ── 5. Daftar Semua Anggota ────────────────────────────────
    story.append(Paragraph(
        f"5. Daftar Semua Anggota (s.d. {judul_periode})", section_sty))

    all_data = [["No", "Nomor Anggota", "Nama", "JK", "Pekerjaan",
                  "No. Telp", "Tgl Daftar", "Status"]]
    for i, ang in enumerate(semua, start=1):
        status_str = "Aktif" if (
            ang.status == "aktif" or
            (ang.tanggal_nonaktif and ang.tanggal_nonaktif > akhir_dt)
        ) else "Nonaktif"
        all_data.append([
            str(i),
            ang.nomor_anggota,
            ang.nama,
            ang.jenis_kelamin or "-",
            ang.pekerjaan or "-",
            ang.no_telp or "-",
            ang.tanggal_daftar.strftime("%d/%m/%Y") if ang.tanggal_daftar else "-",
            status_str,
        ])

    tbl_all = Table(all_data,
                    colWidths=[1*cm, 3.5*cm, 6.5*cm, 2.5*cm, 4.5*cm, 3.5*cm, 2.8*cm, 2.7*cm],
                    repeatRows=1)

    # Warnai baris nonaktif sedikit berbeda
    nonaktif_extras = []
    for i, ang in enumerate(semua, start=1):
        is_nonaktif = (
            ang.status == "nonaktif" and
            ang.tanggal_nonaktif and
            ang.tanggal_nonaktif <= akhir_dt
        )
        if is_nonaktif:
            nonaktif_extras.append(
                ("TEXTCOLOR", (7, i), (7, i), RED)
            )

    tbl_all.setStyle(_tbl_style_header([
        ("ALIGN",  (0, 1), (0, -1), "CENTER"),
        ("ALIGN",  (3, 1), (3, -1), "CENTER"),
        ("ALIGN",  (6, 1), (7, -1), "CENTER"),
    ] + nonaktif_extras))
    story.append(tbl_all)

    # ── Build & return ─────────────────────────────────────────
    doc.build(story)
    output.seek(0)

    response = HttpResponse(output, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nama_file}"'
    return response