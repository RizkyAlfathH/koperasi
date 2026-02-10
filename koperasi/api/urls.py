from django.urls import path
from .views import (
    LoginView, CheckNomorAnggotaView, ResetPasswordView,
    SimpananListView, PenarikanListView,
    PinjamanListView, AngsuranListView, ProfilAnggotaView
)

urlpatterns = [
    path('login/', LoginView.as_view()),
    path('check-nomor-anggota/', CheckNomorAnggotaView.as_view()),
    path('reset-password/', ResetPasswordView.as_view()),

    path('simpanan/<str:nomor_anggota>/', SimpananListView.as_view()),
    path('tarik/<str:nomor_anggota>/', PenarikanListView.as_view()),
    path('pinjaman/<str:nomor_anggota>/', PinjamanListView.as_view()),
    path('angsuran/<int:id_pinjaman>/', AngsuranListView.as_view()),

    path('profil/<str:nomor_anggota>/', ProfilAnggotaView.as_view()),
]
