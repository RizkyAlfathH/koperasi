from django.shortcuts import render
from django.http import HttpResponse
from django.utils.timezone import now
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from datetime import datetime, time
import calendar
import io
import xlsxwriter

from anggota.models import Anggota
from simpanan.models import Simpanan
from pinjaman.models import Pinjaman, Angsuran

# ============================
# VIEW LAPORAN
# ============================
def laporan(request):
    anggota_qs = Anggota.objects.order_by("nama")

    # =========================
    # PARAMETER
    # =========================
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

    # =========================
    # BULANAN
    # =========================
    last_day = calendar.monthrange(tahun_bulan, bulan)[1]
    akhir_bulan = datetime.combine(
        datetime(tahun_bulan, bulan, last_day),
        time(23, 59, 59)
    )

    laporan_bulanan = generate_laporan(anggota_qs, akhir_bulan)

    paginator_bulan = Paginator(laporan_bulanan, per_page_bulan)
    page_bulan = request.GET.get("page_bulan")
    laporan_bulanan = paginator_bulan.get_page(page_bulan)

    # =========================
    # TAHUNAN
    # =========================
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

# =====================================================
# HELPER: GENERATE LAPORAN (SAMA DENGAN TEMPLATE)
# =====================================================
def generate_laporan(anggota_qs, akhir=None):
    laporan = []

    for idx, anggota in enumerate(anggota_qs, start=1):

        # ================= SIMPANAN =================
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

        total_simpanan = pokok + wajib + sukarela

        # ================= PINJAMAN =================
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


# =====================================================
# VIEW EXPORT EXCEL
# =====================================================
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

    # ================== EXCEL ==================
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    bold_center = workbook.add_format({'bold': True, 'align': 'center'})
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
    border_fmt = workbook.add_format({'border': 1})
    money_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0'})

    # ================== SIMPANAN ==================
    ws1 = workbook.add_worksheet("Simpanan")
    ws1.merge_range("A1:F1", "KOPASMEN", bold_center)
    ws1.merge_range("A2:F2", "DAFTAR SIMPANAN POKOK, WAJIB DAN SUKARELA", bold_center)
    ws1.merge_range("A3:F3", f"PER {judul_periode}", bold_center)

    headers = ["NO", "NAMA ANGGOTA", "POKOK", "WAJIB", "SUKARELA", "TOTAL"]
    for col, h in enumerate(headers):
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

    # ================== PINJAMAN ==================
    ws2 = workbook.add_worksheet("Pinjaman")
    ws2.merge_range("A1:F1", "KOPASMEN", bold_center)
    ws2.merge_range("A2:F2", "DAFTAR SALDO PIUTANG", bold_center)
    ws2.merge_range("A3:F3", f"PER {judul_periode}", bold_center)

    headers = ["NO", "NAMA ANGGOTA", "REGULER", "KHUSUS", "BARANG", "TOTAL"]
    for col, h in enumerate(headers):
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
