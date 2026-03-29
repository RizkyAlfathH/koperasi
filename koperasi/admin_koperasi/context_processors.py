# admin_koperasi/context_processors.py
def sidebar_active(request):
    """
    Mengelompokkan semua url_name untuk sidebar,
    supaya menu tetap aktif walau pindah halaman detail/edit/tambah
    """

    return {
        # ================= DASHBOARD =================
        'menu_dashboard_urls': [
            'dashboard_redirect',
            'dashboard_ketua',
            'dashboard_sekretaris',
            'dashboard_bendahara',
        ],
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
            'detail_simpanan',
            'tambah_penarikan',
            'detail_transaksi',
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


# ===============================
# HELP SYSTEM PER HALAMAN
# ===============================
def help_context(request):
    url_name = request.resolver_match.url_name if request.resolver_match else None

    help_data = {

        # ================= DASHBOARD =================
        'dashboard': """
        <div class="help-section">
            <h6>📊 Ringkasan Dashboard</h6>
            <div class="help-item">
                <span class="help-icon">📈</span>
                <p>Menampilkan statistik keseluruhan koperasi secara real-time.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">👥</span>
                <p>Kartu ringkasan menunjukkan jumlah admin, anggota, simpanan, dan pinjaman.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">📅</span>
                <p>Kalender membantu memantau aktivitas harian.</p>
            </div>
        </div>
        """,

        # ================= KELOLA AKUN =================
        'kelola_akun': """
        <div class="help-section">
            <h6>👤 Manajemen Akun</h6>
            <div class="help-item">
                <span class="help-icon">➕</span>
                <p>Tambah akun admin atau anggota baru.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">✏️</span>
                <p>Edit data akun untuk memperbarui informasi.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">🗑️</span>
                <p>Hapus akun jika sudah tidak digunakan.</p>
            </div>
        </div>
        """,

        # ================= SIMPANAN =================
        'daftar_simpanan': """
        <div class="help-section">
            <h6>💰 Manajemen Simpanan</h6>
            <div class="help-item">
                <span class="help-icon">📋</span>
                <p>Menampilkan seluruh data simpanan anggota.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">🔍</span>
                <p>Gunakan fitur pencarian untuk menemukan data lebih cepat.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">➕</span>
                <p>Tambah transaksi simpanan baru melalui tombol tambah.</p>
            </div>
        </div>
        """,

        'detail_simpanan': """
        <div class="help-section">
            <h6>📄 Detail Simpanan</h6>
            <div class="help-item">
                <span class="help-icon">📊</span>
                <p>Menampilkan rincian transaksi simpanan anggota.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">💳</span>
                <p>Termasuk histori setor dan penarikan dana.</p>
            </div>
        </div>
        """,

        # ================= PINJAMAN =================
        'pinjaman_list': """
        <div class="help-section">
            <h6>💳 Manajemen Pinjaman</h6>
            <div class="help-item">
                <span class="help-icon">📋</span>
                <p>Menampilkan daftar seluruh pinjaman anggota.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">🔎</span>
                <p>Klik detail untuk melihat rincian cicilan.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">💵</span>
                <p>Gunakan fitur pembayaran untuk mencatat angsuran.</p>
            </div>
        </div>
        """,

        'detail_pinjaman': """
        <div class="help-section">
            <h6>📄 Detail Pinjaman</h6>
            <div class="help-item">
                <span class="help-icon">📅</span>
                <p>Menampilkan jadwal dan histori pembayaran cicilan.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">💰</span>
                <p>Total sisa pinjaman dan jumlah yang sudah dibayar.</p>
            </div>
        </div>
        """,

        # ================= LAPORAN =================
        'laporan_list': """
        <div class="help-section">
            <h6>📊 Laporan Koperasi</h6>
            <div class="help-item">
                <span class="help-icon">📈</span>
                <p>Menampilkan laporan keuangan dan aktivitas koperasi.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">📤</span>
                <p>Export laporan dalam format Excel atau PDF.</p>
            </div>
            <div class="help-item">
                <span class="help-icon">🗂️</span>
                <p>Gunakan filter untuk menampilkan periode tertentu.</p>
            </div>
        </div>
        """,
    }

    return {
        'help_text': next(
            (text for key, text in help_data.items() if key in (url_name or "")),
            "Belum ada bantuan untuk halaman ini."
        )
    }