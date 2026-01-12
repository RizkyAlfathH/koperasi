from decimal import Decimal

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Q

from .models import Pinjaman
from .forms import PinjamanForm
from admin_koperasi.models import User
from anggota.models import Anggota

@login_required
def pinjaman_list(request):
    data_list = []

    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'nomor')

    anggotas = Anggota.objects.all()

    if search_query:
        anggotas = anggotas.filter(
            Q(nama__icontains=search_query) |
            Q(nomor_anggota__icontains=search_query)
        )

    for anggota in anggotas:

        def total_pinjaman(jenis):
            return (
                Pinjaman.objects.filter(
                    nomor_anggota=anggota,  # ✅ FIX UTAMA
                    id_jenis_pinjaman__nama_jenis=jenis,
                    status='aktif'
                ).aggregate(total=Sum('sisa_pinjaman'))['total'] or 0
            )

        reguler = total_pinjaman('Reguler')
        khusus = total_pinjaman('Khusus')
        barang = total_pinjaman('Barang')

        total = reguler + khusus + barang

        data_list.append({
            'nomor_anggota': anggota.nomor_anggota,
            'nama': anggota.nama,
            'reguler': reguler,
            'khusus': khusus,
            'barang': barang,
            'total': total,
        })

    if sort_by == 'nama':
        data_list.sort(key=lambda x: x['nama'])
    else:
        data_list.sort(key=lambda x: x['nomor_anggota'])

    paginator = Paginator(data_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'pinjaman_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    })

@login_required
@transaction.atomic
def tambah_pinjaman(request):
    user = request.user  # Custom User (Admin)

    # OPTIONAL: batasi role
    if user.role not in ['admin', 'ketua', 'bendahara']:
        messages.error(request, 'Anda tidak memiliki hak akses.')
        return redirect('pinjaman:pinjaman_list')

    if request.method == 'POST':
        form = PinjamanForm(request.POST)
        if form.is_valid():
            pinjaman_baru = form.save(commit=False)

            # SET ADMIN LOGIN
            pinjaman_baru.id_admin = user

            # STATUS AWAL
            pinjaman_baru.status = 'aktif'

            # SISA PINJAMAN AWAL
            pinjaman_baru.sisa_pinjaman = pinjaman_baru.jumlah_pinjaman

            # CEK PINJAMAN AKTIF SEJENIS
            pinjaman_lama = Pinjaman.objects.filter(
                nomor_anggota=pinjaman_baru.nomor_anggota,
                id_jenis_pinjaman=pinjaman_baru.id_jenis_pinjaman,
                status='aktif'
            )

            if pinjaman_lama.exists():
                total_sisa = pinjaman_lama.aggregate(
                    total=Sum('sisa_pinjaman')
                )['total'] or Decimal('0')

                pinjaman_baru.jumlah_pinjaman += total_sisa
                pinjaman_baru.sisa_pinjaman = pinjaman_baru.jumlah_pinjaman

                pinjaman_lama.update(status='digabung')

            pinjaman_baru.save()

            messages.success(request, 'Pinjaman berhasil ditambahkan.')
            return redirect('pinjaman:pinjaman_list')
    else:
        form = PinjamanForm()

    context = {
        'form': form,
        'role': user.role,
        'username': user.username,
    }
    return render(request, 'form/pinjaman_form.html', context)

@login_required
def autocomplete_anggota(request):
    term = request.GET.get('term', '')

    anggota_list = Anggota.objects.filter(
        nama__icontains=term,
        status='aktif'
    )[:10]

    return JsonResponse({
        "results": [
            {
                "id": a.pk,
                "text": f"{a.nomor_anggota} - {a.nama}"
            }
            for a in anggota_list
        ]
    })