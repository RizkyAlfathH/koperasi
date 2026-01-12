from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

User = get_user_model()


def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # redirect sesuai role dengan namespace
            if user.role == 'admin':
                return redirect('admin_koperasi:admin_dashboard')
            elif user.role == 'ketua':
                return redirect('dashboard')
            elif user.role == 'sekretaris':
                return redirect('dashboard')
            elif user.role == 'bendahara':
                return redirect('dashboard')
            else:
                messages.error(request, 'Role tidak dikenali')
                logout(request)
        else:
            messages.error(request, 'Username atau password salah')

    return render(request, 'admin_koperasi/login.html')

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('admin_login')

    return render(request, 'admin_koperasi/dashboard.html')


@login_required
def createpengurus(request):
    if request.user.role != 'admin':
        return redirect('admin_login')

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
            messages.success(request, 'Akun pengurus berhasil dibuat')
            return redirect('admin_dashboard')

    return render(request, 'admin_koperasi/createpengurus.html')


def admin_logout(request):
    logout(request)
    return redirect('admin_koperasi:admin_login') 