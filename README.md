# koperasi
Project koperasi


## 🔧 Git Workflow Tim – Proyek Koperasi Sekolah

### 📌 Struktur Branch
- `main` → Branch final (dinilai / presentasi)
- `develop` → Gabungan semua fitur
- `feature/*` → Branch kerja masing-masing fitur / anggota

### ❌ Aturan Larangan
- DILARANG push langsung ke `main`
- DILARANG push langsung ke `develop`
- Semua perubahan WAJIB lewat Pull Request

### ✅ Alur Kerja Anggota
1. Ambil branch develop
git checkout develop
git pull origin develop


2. Buat branch fitur
git checkout -b feature/nama-fitur


3. Commit perubahan
git add .
git commit -m "feat: deskripsi singkat fitur"


4. Push ke GitHub
git push origin feature/nama-fitur


5. Buat Pull Request
- base: `develop`
- compare: `feature/nama-fitur`

### 🏁 Finalisasi
- Hanya ketua / leader yang merge:
develop → main


### ✍️ Format Commit Message
- `feat:` fitur baru
- `fix:` perbaikan bug
- `refactor:` rapihin kode
