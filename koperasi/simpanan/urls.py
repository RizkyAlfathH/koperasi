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
    # path("detail/<str:nomor_anggota>/<int:jenis_id>/",views.detail_simpanan,name="detail_simpanan"),

    # # EDIT
    # path('<str:kode_anggota>/edit/', views.edit_simpanan, name='edit_simpanan'),

    # # HAPUS
    # path('<str:no_anggota>/hapus/', views.hapus_simpanan, name='hapus_simpanan'),
]
