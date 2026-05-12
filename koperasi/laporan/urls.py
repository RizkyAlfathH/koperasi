from django.urls import path
from . import views

app_name = "laporan"

urlpatterns = [
    # Laporan Keuangan (existing)
    path("keuangan/", views.laporan, name="laporan"),
    path("keuangan/export/", views.export_laporan, name="export_laporan"),

    # Laporan Keanggotaan (new)
    path("keanggotaan/", views.laporan_keanggotaan, name="laporan_keanggotaan"),
    path("keanggotaan/export/", views.export_laporan_keanggotaan, name="export_laporan_keanggotaan"),
    path("keanggotaan/export-pdf/", views.export_laporan_keanggotaan_pdf, name="export_laporan_keanggotaan_pdf"),

    # Redirect root /laporan/ ke keuangan (opsional, bisa dihapus)
    path("", views.laporan, name="laporan_index"),
]