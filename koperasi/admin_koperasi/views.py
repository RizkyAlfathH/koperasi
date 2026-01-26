from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from admin_koperasi.models import RolePermission
from django.db import transaction

User = get_user_model()


def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            # redirect berdasarkan role
            if user and user.role == 'admin':
                login(request, user)
                return redirect("anggota:dashboard_redirect")
            else:
                return redirect('anggota:dashboard_redirect')

        messages.error(request, 'Username atau password salah')

    return render(request, 'admin_koperasi/login.html')

@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_koperasi:admin_login')


# ================= DASHBOARD =================
@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('admin_koperasi:admin_login')

    return render(request, 'admin_koperasi/dashboard.html')


@login_required
def role_hakakses(request):
    if request.user.role != "admin":
        return redirect("admin_koperasi:admin_login")

    # =============================
    # MASTER PERMISSIONS
    # =============================
    permissions = [
        {"code": "dashboard_ketua", "name": "Dashboard Ketua"},
        {"code": "dashboard_sekretaris", "name": "Dashboard Sekretaris"},
        {"code": "dashboard_bendahara", "name": "Dashboard Bendahara"},
        {"code": "kelola_anggota", "name": "Kelola Anggota"},
        {"code": "simpanan", "name": "Simpanan"},
        {"code": "pinjaman", "name": "Pinjaman"},
        {"code": "laporan", "name": "Laporan"},
    ]

    # =============================
    # HANDLE POST (SIMPAN KE DB)
    # =============================
    if request.method == "POST":
        ketua_permissions = request.POST.getlist("ketua_permissions")
        sekretaris_permissions = request.POST.getlist("sekretaris_permissions")
        bendahara_permissions = request.POST.getlist("bendahara_permissions")

        with transaction.atomic():
            RolePermission.objects.filter(
                role__in=["ketua", "sekretaris", "bendahara"]
            ).delete()

            for p in ketua_permissions:
                RolePermission.objects.create(role="ketua", permission_code=p)

            for p in sekretaris_permissions:
                RolePermission.objects.create(role="sekretaris", permission_code=p)

            for p in bendahara_permissions:
                RolePermission.objects.create(role="bendahara", permission_code=p)

        messages.success(request, "Hak akses berhasil disimpan")
        return redirect("admin_koperasi:role_hakakses")

    # =============================
    # LOAD DATA DARI DB
    # =============================
    role_permissions = {
        "ketua": [],
        "sekretaris": [],
        "bendahara": [],
    }

    for rp in RolePermission.objects.all():
        role_permissions[rp.role].append(rp.permission_code)

    # fallback default kalau DB masih kosong
    if not RolePermission.objects.exists():
        role_permissions["ketua"] = [p["code"] for p in permissions]
        role_permissions["sekretaris"] = [
            "dashboard_sekretaris",
            "kelola_anggota",
        ]
        role_permissions["bendahara"] = [
            "dashboard_bendahara",
            "simpanan",
            "pinjaman",
            "laporan",
        ]

    return render(
        request,
        "admin_koperasi/manajemen_user/role_hakakases.html",
        {
            "permissions": permissions,
            "role_permissions": role_permissions,
        }
    )


# ================= PENGURUS =================
@login_required
def pengurus(request):
    if request.user.role != 'admin':
        return redirect('admin_koperasi:admin_login')

    return render(request, 'admin_koperasi/struktur_koperasi/pengurus.html')


@login_required
def createpengurus(request):
    if request.user.role != 'admin':
        return redirect('admin_koperasi:admin_login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username sudah digunakan')
        else:
            User.objects.create_user(
                username=username,
                password=password,
                role=role
            )
            messages.success(request, 'Pengurus berhasil ditambahkan')
            return redirect('admin_koperasi:pengurus')

    return render(request, 'admin_koperasi/struktur_koperasi/createpengurus.html')


# ================= SISTEM =================
@login_required
def log_aktifitas(request):
    if request.user.role != 'admin':
        return redirect('admin_koperasi:admin_login')

    return render(request, 'admin_koperasi/sistem/log_aktifitas.html')


@login_required
def pengaturan_sistem(request):
    if request.user.role != 'admin':
        return redirect('admin_koperasi:admin_login')

    return render(request, 'admin_koperasi/sistem/pengaturan_sistem.html')
