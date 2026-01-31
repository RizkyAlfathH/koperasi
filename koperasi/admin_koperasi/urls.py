from django.urls import path
from . import views

app_name = 'admin_koperasi'

urlpatterns = [

    # ===== AUTH =====
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),

    # ===== DASHBOARD =====
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # ===== ROLE & HAK AKSES =====
    path(
        'role-hak-akses/',
        views.role_hakakses,
        name='role_hakakses'
    ),

    # ===== PENGURUS (CRUD) =====
    path(
        'pengurus/',
        views.pengurus,
        name='pengurus'
    ),
    path(
        'pengurus/tambah/',
        views.createpengurus,
        name='createpengurus'
    ),

    # ===== SISTEM =====
    path(
        'log-aktifitas/',
        views.log_aktifitas,
        name='log_aktifitas'
    ),
    path(
        'pengaturan-sistem/',
        views.pengaturan_sistem,
        name='pengaturan_sistem'
    ),
]
