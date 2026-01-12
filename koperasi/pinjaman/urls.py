from django.urls import path
from . import views

app_name = 'pinjaman'

urlpatterns = [
    path('', views.pinjaman_list, name='pinjaman_list'),
    path('tambah/', views.tambah_pinjaman, name='pinjaman_form'),
    path("autocomplete-anggota/", views.autocomplete_anggota, name="autocomplete_anggota"),
]
