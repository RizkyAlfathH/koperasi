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
    if request.user.is_authenticated:
        return redirect('anggota:dashboard_redirect')

    errors = {}

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # validasi kosong
        if not username:
            errors['username'] = 'Username wajib diisi.'

        if not password:
            errors['password'] = 'Password wajib diisi.'

        # cek login kalau tidak ada error
        if not errors:
            user = authenticate(request, username=username, password=password)

            if user is None:
                # cek username di custom user model
                if not User.objects.filter(username=username).exists():
                    errors['username'] = 'Username tidak ditemukan.'
                else:
                    errors['password'] = 'Password salah.'
            else:
                login(request, user)
                return redirect('anggota:dashboard_redirect')

    return render(request, 'admin_koperasi/login.html', {
        'errors': errors
    })

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

    permissions = [
        {"code": "dashboard_ketua", "name": "Dashboard Ketua"},
        {"code": "dashboard_sekretaris", "name": "Dashboard Sekretaris"},
        {"code": "dashboard_bendahara", "name": "Dashboard Bendahara"},
        {"code": "kelola_anggota", "name": "Kelola Anggota"},
        {"code": "simpanan", "name": "Simpanan"},
        {"code": "pinjaman", "name": "Pinjaman"},
        {"code": "laporan", "name": "Laporan"},
    ]

    roles = ["ketua", "sekretaris", "bendahara"]

    # ================= POST =================
    if request.method == "POST":
        with transaction.atomic():
            for role in roles:
                RolePermission.objects.filter(role=role).delete()

                selected_permissions = request.POST.getlist(f"{role}_permissions")
                for p in selected_permissions:
                    RolePermission.objects.create(
                        role=role,
                        permission_code=p
                    )

        messages.success(request, "Hak akses berhasil disimpan")
        return redirect("admin_koperasi:role_hakakses")

    # ================= LOAD =================
    role_permissions = {role: [] for role in roles}

    data = RolePermission.objects.all()

    # === DEFAULT JIKA DB KOSONG ===
    if not data.exists():
        default_data = {
            "ketua": [p["code"] for p in permissions],
            "sekretaris": [
                "dashboard_sekretaris",
                "kelola_anggota",
            ],
            "bendahara": [
                "dashboard_bendahara",
                "simpanan",
                "pinjaman",
                "laporan",
            ],
        }

        for role, perms in default_data.items():
            for p in perms:
                RolePermission.objects.create(role=role, permission_code=p)

        data = RolePermission.objects.all()

    for rp in data:
        role_permissions[rp.role].append(rp.permission_code)

    return render(
        request,
        "admin_koperasi/manajemen_user/role_hakakses.html",
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
