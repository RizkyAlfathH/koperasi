from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from admin_koperasi.models import RolePermission
from django.db import transaction
from .forms import PengurusForm
from .decorators import admin_only

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

@login_required
@admin_only
def pengurus_list(request, pk=None):
    pengurus = User.objects.filter(
        role__in=['ketua', 'sekretaris', 'bendahara']
    )

    if pk:
        instance = get_object_or_404(User, pk=pk)
        title = "Edit Pengurus"
    else:
        instance = None
        title = "Tambah Pengurus"

    form = PengurusForm(request.POST or None, instance=instance)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect('admin_koperasi:pengurus_list')

    return render(request, 'admin_koperasi/manajemen_user/pengurus_list.html', {
        'pengurus': pengurus,
        'form': form,
        'title': title,
        'edit_id': pk
    })

@login_required
@admin_only
def pengurus_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.delete()
        return redirect('admin_koperasi:pengurus_list')
    return render(request, 'admin_koperasi/manajemen_user/pengurus_confirm_delete.html', {
        'user': user
    })

@login_required
@admin_only
def pengurus_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        user.is_active = not user.is_active
        user.save()

    return redirect('admin_koperasi:pengurus_list')
