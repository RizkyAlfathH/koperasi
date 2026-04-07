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

# fungsi view untuk menampilkan laporan
def laporan(request):

    # query ORM (method) untuk mengambil data anggota dan diurutkan
    anggota_qs = Anggota.objects.order_by("nama")

    # parameter dari request GET (method dari objek request)
    bulan = int(request.GET.get("bulan", now().month))
    tahun_bulan = int(request.GET.get("tahun", now().year))
    tahun_tahunan = int(request.GET.get("tahun_tahunan", now().year))

    # parameter pagination
    per_page_bulan = int(request.GET.get("per_page_bulan", 10))
    per_page_tahun = int(request.GET.get("per_page_tahun", 10))

    # list (objek) pilihan bulan
    bulan_choices = [
        (1, "Januari"), (2, "Februari"), (3, "Maret"),
        (4, "April"), (5, "Mei"), (6, "Juni"),
        (7, "Juli"), (8, "Agustus"), (9, "September"),
        (10, "Oktober"), (11, "November"), (12, "Desember"),
    ]

    # range tahun (objek range)
    tahun_range = range(2020, now().year + 1)

    # menghitung hari terakhir dalam bulan
    last_day = calendar.monthrange(tahun_bulan, bulan)[1]

    # membuat objek datetime akhir bulan
    akhir_bulan = datetime.combine(
        datetime(tahun_bulan, bulan, last_day),
        time(23, 59, 59)
    )

    # memanggil fungsi custom untuk generate laporan bulanan
    laporan_bulanan = generate_laporan(anggota_qs, akhir_bulan)

    # paginator (objek class Paginator)
    paginator_bulan = Paginator(laporan_bulanan, per_page_bulan)

    # mengambil nomor halaman dari GET
    page_bulan = request.GET.get("page_bulan")

    # method paginator untuk ambil halaman
    laporan_bulanan = paginator_bulan.get_page(page_bulan)

    # membuat objek datetime akhir tahun
    akhir_tahun = datetime.combine(
        datetime(tahun_tahunan, 12, 31),
        time(23, 59, 59)
    )

    # generate laporan tahunan
    laporan_tahunan = generate_laporan(anggota_qs, akhir_tahun)

    # paginator laporan tahunan
    paginator_tahun = Paginator(laporan_tahunan, per_page_tahun)

    page_tahun = request.GET.get("page_tahun")

    laporan_tahunan = paginator_tahun.get_page(page_tahun)

    # render template dengan context (dictionary)
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

# fungsi helper untuk generate laporan (fungsi biasa, bukan view)
def generate_laporan(anggota_qs, akhir=None):

    laporan = []  # list (objek) untuk menampung hasil

    # loop queryset anggota (enumerate = fungsi Python)
    for idx, anggota in enumerate(anggota_qs, start=1):

        # filter dinamis (dictionary sebagai objek)
        simpanan_filter = {"anggota": anggota}
        if akhir:
            simpanan_filter["tanggal__lte"] = akhir

        # query ORM + aggregate (method)
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

        # perhitungan total (operasi aritmatika)
        total_simpanan = pokok + wajib + sukarela

        # inisialisasi variabel pinjaman
        total_reguler = total_khusus = total_barang = 0

        # query pinjaman
        pinjaman_qs = Pinjaman.objects.filter(
            nomor_anggota=anggota,
            tanggal_meminjam__lte=akhir if akhir else now()
        )

        # loop jenis pinjaman
        for jenis in ["Reguler", "Khusus", "Barang"]:

            # ambil data terbaru (method order_by + first)
            pinjaman = pinjaman_qs.filter(
                id_jenis_pinjaman__nama_jenis=jenis
            ).order_by("-tanggal_meminjam").first()

            # validasi jika tidak ada data
            if not pinjaman:
                continue

            # hitung jumlah cicilan (method count)
            cicilan = Angsuran.objects.filter(
                id_pinjaman=pinjaman,
                tanggal_bayar__lte=akhir if akhir else now()
            ).count()

            # ambil nilai angsuran
            angsuran_pokok = pinjaman.angsuran_per_bulan or 0

            # hitung sisa pinjaman
            sisa_pinjaman = pinjaman.jumlah_pinjaman - (cicilan * angsuran_pokok)

            # validasi agar tidak negatif
            if sisa_pinjaman <= 0:
                continue

            # perhitungan jasa
            if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
                jasa = sisa_pinjaman * (pinjaman.jasa_persen / 100)
            else:
                jasa = pinjaman.jumlah_pinjaman * (pinjaman.jasa_persen / 100)

            total_sisa = sisa_pinjaman + jasa

            # penjumlahan berdasarkan jenis
            if jenis == "Reguler":
                total_reguler += total_sisa
            elif jenis == "Khusus":
                total_khusus += total_sisa
            elif jenis == "Barang":
                total_barang += total_sisa

        # append data ke list laporan (dictionary)
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


# fungsi view untuk export laporan ke excel
def export_laporan(request):

    # mengambil parameter GET (method dari objek request)
    periode = request.GET.get("periode", "bulan")
    bulan = int(request.GET.get("bulan", now().month))
    tahun = int(request.GET.get("tahun", now().year))

    # query anggota
    anggota_qs = Anggota.objects.order_by("nama")

    # menentukan periode laporan
    if periode == "tahun":
        akhir = datetime.combine(datetime(tahun, 12, 31), time(23, 59, 59))
        judul_periode = f"31 DESEMBER {tahun}"
        nama_file = f"Laporan Tahun {tahun}.xlsx"
    else:
        last_day = calendar.monthrange(tahun, bulan)[1]
        akhir = datetime.combine(datetime(tahun, bulan, last_day), time(23, 59, 59))

        # list bulan (objek list)
        nama_bulan = [
            "", "JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI",
            "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"
        ][bulan]

        judul_periode = f"{last_day} {nama_bulan} {tahun}"
        nama_file = f"Laporan {nama_bulan} {tahun}.xlsx"

    # panggil fungsi helper
    laporan = generate_laporan(anggota_qs, akhir)

    # membuat objek file excel (class Workbook)
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # format excel (objek format)
    bold_center = workbook.add_format({'bold': True, 'align': 'center'})
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'align': 'center'})
    border_fmt = workbook.add_format({'border': 1})
    money_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0'})

    # worksheet simpanan (objek worksheet)
    ws1 = workbook.add_worksheet("Simpanan")

    # method merge_range dan write
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

    # set lebar kolom
    ws1.set_column("A:A", 5)
    ws1.set_column("B:B", 30)
    ws1.set_column("C:F", 15)

    # worksheet pinjaman
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

    # menutup workbook
    workbook.close()
    output.seek(0)

    # membuat response file download
    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # header response (method set header)
    response["Content-Disposition"] = f'attachment; filename="{nama_file}"'

    return response