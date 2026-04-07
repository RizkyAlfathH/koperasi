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

# fungsi (function) untuk login admin
def admin_login(request):
    # request = objek HttpRequest dari Django

    # pengecekan: jika user sudah login
    if request.user.is_authenticated:
        return redirect('anggota:dashboard_redirect')
        # redirect = fungsi bawaan Django untuk pindah halaman

    errors = {}  # dictionary (objek) untuk menyimpan error validasi

    # pengecekan method request (GET / POST)
    if request.method == 'POST':
        # mengambil data dari form (method dari objek request)
        username = request.POST.get('username')
        password = request.POST.get('password')

        # validasi input kosong
        if not username:
            errors['username'] = 'Username wajib diisi.'

        if not password:
            errors['password'] = 'Password wajib diisi.'

        # proses login jika tidak ada error
        if not errors:
            # authenticate = fungsi untuk cek username & password
            user = authenticate(request, username=username, password=password)

            # jika user tidak ditemukan / gagal login
            if user is None:
                # query ke database (method ORM Django)
                if not User.objects.filter(username=username).exists():
                    errors['username'] = 'Username tidak ditemukan.'
                else:
                    errors['password'] = 'Password salah.'
            else:
                # login = fungsi untuk membuat session user
                login(request, user)
                return redirect('anggota:dashboard_redirect')

    # render = fungsi untuk menampilkan template
    return render(request, 'admin_koperasi/login.html', {
        'errors': errors
    })


# fungsi untuk logout user
def admin_logout(request):
    logout(request)  # logout = fungsi Django untuk menghapus session
    return redirect('admin_koperasi:admin_login')


# fungsi dashboard admin
@login_required  # decorator (fungsi pembungkus) untuk cek login
def admin_dashboard(request):
    # pengecekan role user
    if request.user.role != 'admin':
        return redirect('admin_koperasi:admin_login')

    return render(request, 'admin_koperasi/dashboard.html')


# fungsi untuk mengatur hak akses role
@login_required
def role_hakakses(request):

    # validasi hanya admin
    if request.user.role != "admin":
        return redirect("admin_koperasi:admin_login")

    # list (objek) berisi data permission
    permissions = [
        {"code": "dashboard_ketua", "name": "Dashboard Ketua"},
        {"code": "dashboard_sekretaris", "name": "Dashboard Sekretaris"},
        {"code": "dashboard_bendahara", "name": "Dashboard Bendahara"},
        {"code": "kelola_anggota", "name": "Kelola Anggota"},
        {"code": "simpanan", "name": "Simpanan"},
        {"code": "pinjaman", "name": "Pinjaman"},
        {"code": "laporan", "name": "Laporan"},
    ]

    # list role
    roles = ["ketua", "sekretaris", "bendahara"]

    # proses jika method POST
    if request.method == "POST":
        # transaction.atomic = context manager untuk transaksi database
        with transaction.atomic():
            for role in roles:
                # hapus data lama (query ORM)
                RolePermission.objects.filter(role=role).delete()

                # ambil data checkbox dari form
                selected_permissions = request.POST.getlist(f"{role}_permissions")

                # simpan data baru ke database
                for p in selected_permissions:
                    RolePermission.objects.create(
                        role=role,
                        permission_code=p
                    )

        messages.success(request, "Hak akses berhasil disimpan")
        return redirect("admin_koperasi:role_hakakses")

    # dictionary untuk menampung hasil permission per role
    role_permissions = {role: [] for role in roles}

    # ambil semua data dari database
    data = RolePermission.objects.all()

    # jika database kosong, isi default
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

        # insert data default
        for role, perms in default_data.items():
            for p in perms:
                RolePermission.objects.create(role=role, permission_code=p)

        data = RolePermission.objects.all()

    # mapping data ke dictionary
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


# fungsi untuk menampilkan dan tambah/edit pengurus
@login_required
@admin_only  # decorator custom (fungsi pembatas akses admin)
def pengurus_list(request, pk=None):

    # query data user berdasarkan role
    pengurus = User.objects.filter(
        role__in=['ketua', 'sekretaris', 'bendahara']
    )

    # cek apakah mode edit atau tambah
    if pk:
        instance = get_object_or_404(User, pk=pk)
        title = "Edit Pengurus"
    else:
        instance = None
        title = "Tambah Pengurus"

    # form = objek dari class PengurusForm
    form = PengurusForm(request.POST or None, instance=instance)

    # validasi dan simpan data
    if request.method == "POST" and form.is_valid():
        form.save()  # method dari class form
        return redirect('admin_koperasi:pengurus_list')

    return render(request, 'admin_koperasi/manajemen_user/pengurus_list.html', {
        'pengurus': pengurus,
        'form': form,
        'title': title,
        'edit_id': pk
    })


# fungsi untuk menghapus pengurus
@login_required
@admin_only
def pengurus_delete(request, pk):

    # ambil objek user dari database
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        user.delete()  # method untuk hapus objek
        return redirect('admin_koperasi:pengurus_list')

    return render(request, 'admin_koperasi/manajemen_user/pengurus_confirm_delete.html', {
        'user': user
    })


# fungsi untuk mengaktifkan / nonaktifkan user
@login_required
@admin_only
def pengurus_toggle(request, pk):

    # ambil objek user
    user = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        # toggle status aktif
        user.is_active = not user.is_active
        user.save()  # method untuk menyimpan perubahan

    return redirect('admin_koperasi:pengurus_list')