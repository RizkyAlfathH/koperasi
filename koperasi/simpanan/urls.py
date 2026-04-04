from django.urls import path
from . import views

app_name = "simpanan"


urlpatterns = [
    # LIST
    path('', views.daftar_simpanan, name='daftar_simpanan'),

    # TAMBAH
    path('tambah/', views.tambah_simpanan, name='simpanan_form'),
    path("cek-dana-sosial/", views.cek_dana_sosial, name="cek_dana_sosial"),
    path("autocomplete-anggota/", views.autocomplete_anggota, name="autocomplete_anggota"),

    #SIMPANAN PER ANGGOTA
    path("<str:nomor_anggota>/",views.simpanan_anggota,name="simpanan_anggota"),

    #PENARIKAN SIMPANAN
    path("penarikan/<str:nomor_anggota>/<int:jenis>/",views.tambah_penarikan,name="tambah_penarikan"),

    # DETAIL SIMPANAN PER ANGGOTA
    path("detail/<str:nomor_anggota>/<int:jenis_id>/",views.detail_simpanan,name="detail_simpanan"),

    path("transaksi/<int:id>/",views.detail_transaksi,name="detail_transaksi"),

    path("kwitansi/<int:history_id>/", views.download_kwitansi, name="download_kwitansi"),

    # HAPUS SIMPANAN
    path("hapus/<str:nomor_anggota>/", views.hapus_simpanan, name="hapus_simpanan"),
    path("hapus-transaksi/<str:nomor_anggota>/<int:jenis_id>/", views.hapus_transaksi_terakhir, name="hapus_transaksi_terakhir"),
]