import re
import openpyxl
from anggota.models import Anggota
from .models import JenisSimpanan


# ================================================================
# STEP 1: normalisasi nama
# hapus gelar (S.Pd, SE, dll), ubah ke huruf kecil, hapus spasi dobel
# ================================================================
def bersihkan_nama(nama):
    if not nama:
        return ''
    nama = str(nama)
    # hapus gelar yang diawali koma atau spasi
    nama = re.sub(
        r',?\s*(S\.Pd|S\.E|SE|S\.Kom|SST|S\.T|M\.Pd|M\.Si|M\.M|'
        r'Dr|Drs|Dra|S\.Ag|S\.H|M\.H|S\.Sos|M\.Sc|Ph\.D)\.?',
        '', nama, flags=re.IGNORECASE
    )
    return nama.strip().strip(',').strip().lower()


# ================================================================
# STEP 2: deteksi apakah file ini format TPP atau format Laporan App
# ================================================================
def deteksi_format(wb):
    ws = wb.active
    nilai_a1 = str(ws.cell(1, 1).value or '').strip().upper()

    # format Laporan App: cell A1 berisi nama koperasi
    if 'KOPASMEN' in nilai_a1 or 'KOPERASI' in nilai_a1:
        return 'laporan'

    # format TPP: cell A1 berisi 'NO' dan ada kolom NAMA
    if nilai_a1 == 'NO':
        return 'tpp'

    return None


# ================================================================
# STEP 3A: baca file format TPP
# struktur: 2 baris header, data mulai baris 3
# kolom penting: NAMA, POKOK/SIMPOK, WAJIB, SUKARELA, DANSOS
# ================================================================
def baca_tpp(ws):
    # baca header dari baris 1 dan 2 untuk temukan posisi kolom
    header1 = [str(c.value or '').upper().strip() for c in ws[1]]
    header2 = [str(c.value or '').upper().strip() for c in ws[2]]

    # cari index kolom berdasarkan kata kunci
    def cari(kw1, kw2=None):
        for i, h in enumerate(header1):
            if kw1 in h or (kw2 and kw2 in h):
                return i
        for i, h in enumerate(header2):
            if kw1 in h or (kw2 and kw2 in h):
                return i
        return None

    i_nama     = cari('NAMA')
    i_pokok    = cari('POKOK', 'SIMPOK')
    i_wajib    = cari('WAJIB')
    i_sukarela = cari('SUKARELA')
    i_dansos   = cari('DANSOS')

    def angka(row, idx):
        if idx is None:
            return 0
        try:
            v = row[idx]
            return float(v) if v else 0
        except:
            return 0

    hasil = []
    for row in ws.iter_rows(min_row=3, values_only=True):
        nama = row[i_nama] if i_nama is not None else None
        if not nama:
            continue
        if str(nama).strip().upper() in ('TOTAL', 'JUMLAH'):
            continue

        hasil.append({
            'nama_di_file' : str(nama).strip(),
            'cari_pakai'   : 'nama',        # nanti dicocokkan pakai nama
            'nomor_anggota': '',
            'pokok'        : angka(row, i_pokok),
            'wajib'        : angka(row, i_wajib),
            'sukarela'     : angka(row, i_sukarela),
            'dansos'       : angka(row, i_dansos),
        })
    return hasil


# ================================================================
# STEP 3B: baca file format Laporan App
# struktur: 5 baris header, data mulai baris 6
# kolom: NO(=nomor anggota) | NAMA | POKOK | WAJIB | SUKARELA | TOTAL
# ================================================================
def baca_laporan(wb):
    # cari sheet bernama 'Simpanan'
    nama_sheets = [s.lower() for s in wb.sheetnames]
    if 'simpanan' not in nama_sheets:
        return None, "Sheet 'Simpanan' tidak ditemukan"

    ws = wb[wb.sheetnames[nama_sheets.index('simpanan')]]

    def angka(val):
        try:
            return float(val) if val else 0
        except:
            return 0

    hasil = []
    for row in ws.iter_rows(min_row=6, values_only=True):
        nomor = row[0]
        nama  = row[1]
        if not nomor or not nama:
            continue
        if str(nama).strip().upper() in ('TOTAL', 'JUMLAH'):
            continue

        hasil.append({
            'nama_di_file' : str(nama).strip(),
            'cari_pakai'   : 'nomor',       # dicocokkan pakai nomor anggota
            'nomor_anggota': str(nomor).strip(),
            'pokok'        : angka(row[2]),
            'wajib'        : angka(row[3]),
            'sukarela'     : angka(row[4]),
            'dansos'       : 0,
        })
    return hasil, None


# ================================================================
# STEP 4: cocokkan setiap baris ke anggota di database
# ================================================================
def cocokkan_ke_db(baris_list):
    # ambil semua anggota aktif sekali saja (efisien)
    semua_anggota = Anggota.objects.filter(status='aktif')

    # buat 2 mapping: by nama (bersih) dan by nomor anggota
    by_nama  = {bersihkan_nama(a.nama): a for a in semua_anggota}
    by_nomor = {a.nomor_anggota.strip(): a for a in semua_anggota}

    # ambil objek jenis simpanan
    j_pokok    = JenisSimpanan.objects.filter(nama_jenis='Pokok').first()
    j_wajib    = JenisSimpanan.objects.filter(nama_jenis='Wajib').first()
    j_sukarela = JenisSimpanan.objects.filter(nama_jenis='Sukarela').first()

    hasil = []
    for b in baris_list:
        # coba cocokkan ke anggota
        if b['cari_pakai'] == 'nomor':
            anggota = by_nomor.get(b['nomor_anggota'])
        else:
            anggota = by_nama.get(bersihkan_nama(b['nama_di_file']))

        hasil.append({
            # info dari file
            'nama_di_file'     : b['nama_di_file'],

            # hasil matching
            'cocok'            : anggota is not None,
            'anggota_id'       : anggota.nomor_anggota if anggota else '',
            'nama_anggota'     : anggota.nama if anggota else '',

            # nilai simpanan
            'pokok'            : b['pokok'],
            'wajib'            : b['wajib'],
            'sukarela'         : b['sukarela'],
            'dansos'           : b['dansos'],

            # id jenis simpanan (untuk hidden input di form)
            'id_pokok'         : j_pokok.pk if j_pokok else '',
            'id_wajib'         : j_wajib.pk if j_wajib else '',
            'id_sukarela'      : j_sukarela.pk if j_sukarela else '',
        })

    return hasil


# ================================================================
# FUNGSI UTAMA: dipanggil dari view
# input: file object dari request.FILES
# output: (list_baris, pesan_error)
# ================================================================
def proses_file_import(file):
    try:
        wb = openpyxl.load_workbook(file, data_only=True)
    except Exception as e:
        return [], f"File tidak bisa dibaca: {e}"

    format_file = deteksi_format(wb)

    if format_file == 'tpp':
        baris_list = baca_tpp(wb.active)

    elif format_file == 'laporan':
        baris_list, err = baca_laporan(wb)
        if err:
            return [], err

    else:
        return [], "Format file tidak dikenali. Gunakan file TPP atau file Laporan dari aplikasi."

    if not baris_list:
        return [], "Tidak ada data yang terbaca dari file."

    return cocokkan_ke_db(baris_list), None