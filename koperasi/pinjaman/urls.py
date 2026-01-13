# pinjaman/urls.py
from django.urls import path
from . import views

app_name = 'pinjaman'

urlpatterns = [
    path('', views.pinjaman_list, name='pinjaman_list'),
    path('tambah/', views.tambah_pinjaman, name='pinjaman_form'),
    path('autocomplete-anggota/', views.autocomplete_anggota, name='autocomplete_anggota'),

    # 🔥 BARU
    path(
        'anggota/<str:nomor_anggota>/',
        views.pinjaman_anggota,
        name='pinjaman_anggota'
    ),

    path('<int:id_pinjaman>/', views.detail_pinjaman, name='detail_pinjaman'),
]
