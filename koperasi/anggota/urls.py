from django.urls import path
from .views import (
    kelola_akun,
    tambah_admin,
    edit_admin,
    hapus_admin,
    tambah_anggota,
    edit_anggota,
    hapus_anggota,
    detail_admin,
    detail_anggota,
    export_excel_anggota,
    export_pdf_anggota,
    import_excel_anggota,
)


urlpatterns = [
    # 🔹 kelola akun (role-based)
    path("", kelola_akun, name="kelola_akun"),

    # 🔹 ADMIN
    path("tambah/admin/", tambah_admin, name="tambah_admin"),
    path("edit/admin/<int:user_id>/", edit_admin, name="edit_admin"),
    path("hapus/admin/<int:user_id>/", hapus_admin, name="hapus_admin"),

    # 🔹 ANGGOTA
    path("tambah/anggota/", tambah_anggota, name="tambah_anggota"),
    path("edit/anggota/<str:nomor_anggota>/", edit_anggota, name="edit_anggota"),
    path("hapus/anggota/<str:nomor_anggota>/", hapus_anggota, name="hapus_anggota"),

    # 🔹 DETAIL
    path("detail/admin/<int:user_id>/", detail_admin, name="detail_admin"),
    path("detail/anggota/<str:nomor_anggota>/", detail_anggota, name="detail_anggota"),

    # 🔹 IMPORT / EXPORT
    path("export/excel/", export_excel_anggota, name="export_excel_anggota"),
    path("export/pdf/", export_pdf_anggota, name="export_pdf_anggota"),
    path("import/excel/", import_excel_anggota, name="import_excel_anggota"),
]
