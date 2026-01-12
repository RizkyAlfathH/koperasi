from django.urls import path
from .views import (
    admin_login,
    admin_dashboard,
    admin_logout,
    createpengurus
)

app_name = 'admin_koperasi'

urlpatterns = [
    path('login/', admin_login, name='admin_login'),
    path('dashboard/', admin_dashboard, name='admin_dashboard'),
    path('pengurus/tambah/', createpengurus, name='createpengurus'),
    path('logout/', admin_logout, name='admin_logout'),
]