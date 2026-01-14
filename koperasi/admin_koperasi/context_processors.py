# admin_koperasi/context_processors.py
def sidebar_active(request):
    """
    Mengelompokkan semua url_name untuk sidebar,
    supaya menu tetap aktif walau pindah halaman detail/edit/tambah
    """

    return {
        # Menu Kelola Akun (Admin + Anggota)
        'menu_akun_urls': [
            'kelola_akun',
            'tambah_admin',
            'edit_admin',
            'hapus_admin',
            'detail_admin',
            'tambah_anggota',
            'edit_anggota',
            'detail_anggota',
            'hapus_anggota',
            'export_excel_anggota',
            'export_pdf_anggota',
            'import_excel_anggota',
        ],

        # Menu Simpanan
        'menu_simpanan_urls': [
            'daftar_simpanan',
            'simpanan_form',
            'simpanan_anggota',
        ],

        # Menu Pinjaman
        'menu_pinjaman_urls': [
            'pinjaman_list',
            'pinjaman_form',
            'pinjaman_anggota',
            'detail_pinjaman',
            'bayar_pinjaman',
        ],

        # Tambahkan menu lain jika ada
    }
