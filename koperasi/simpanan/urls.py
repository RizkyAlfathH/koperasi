from django.urls import path
from . import views

app_name = "simpanan"

urlpatterns = [
    # LIST
    path('', views.daftar_simpanan, name='daftar_simpanan'),

    # TAMBAH
    path('tambah/', views.tambah_simpanan, name='simpanan_form'),
    path('cek-dana-sosial/', views.cek_dana_sosial, name="cek_dana_sosial"),
    path('autocomplete-anggota/', views.autocomplete_anggota, name="autocomplete_anggota"),

    # IMPORT — harus di atas <str:nomor_anggota>/ !
    path('import/', views.import_simpanan, name='import_simpanan'),
    path('import/proses/', views.proses_import_simpanan, name='proses_import_simpanan'),

    # DETAIL & AKSI — harus di atas <str:nomor_anggota>/ !
    path('penarikan/<str:nomor_anggota>/<int:jenis>/', views.tambah_penarikan, name="tambah_penarikan"),
    path('detail/<str:nomor_anggota>/<int:jenis_id>/', views.detail_simpanan, name="detail_simpanan"),
    path('transaksi/<int:id>/', views.detail_transaksi, name="detail_transaksi"),
    path('kwitansi/<int:history_id>/', views.download_kwitansi, name="download_kwitansi"),

    # SIMPANAN PER ANGGOTA — paling bawah karena <str> nangkep semua kata
    path('<str:nomor_anggota>/', views.simpanan_anggota, name="simpanan_anggota"),
]