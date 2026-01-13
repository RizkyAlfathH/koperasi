from datetime import datetime
from decimal import Decimal

from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Q

from .models import Angsuran, Pinjaman
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
                    nomor_anggota=anggota,
                    id_jenis_pinjaman__nama_jenis=jenis,
                    status='aktif'
                ).aggregate(total=Sum('sisa_pinjaman'))['total'] or 0
            )

        reguler = total_pinjaman('Reguler')
        khusus = total_pinjaman('Khusus')
        barang = total_pinjaman('Barang')

        total = reguler + khusus + barang

        # 🔥 AMBIL PINJAMAN AKTIF (1 TERBARU)
        pinjaman_aktif = Pinjaman.objects.filter(
            nomor_anggota=anggota,
            status='aktif'
        ).order_by('-tanggal_meminjam').first()

        data_list.append({
            'id_pinjaman': pinjaman_aktif.id_pinjaman if pinjaman_aktif else None,
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

@login_required
def pinjaman_anggota(request, nomor_anggota):
    anggota = get_object_or_404(
        Anggota,
        nomor_anggota=nomor_anggota
    )

    pinjaman_qs = Pinjaman.objects.filter(
        nomor_anggota=anggota
    ).select_related(
        'id_jenis_pinjaman',
        'id_kategori_jasa'
    ).order_by('tanggal_meminjam')

    pinjaman_aktif = []
    riwayat_pinjaman = []

    for pinjaman in pinjaman_qs:

        # =========================
        # HITUNG CICILAN TERBAYAR
        # =========================
        angsuran_pokok = pinjaman.angsuran_per_bulan or Decimal('0')

        jumlah_cicilan_terbayar = Angsuran.objects.filter(
            id_pinjaman=pinjaman,
            tipe_bayar='cicilan'
        ).count()

        sisa_pinjaman = pinjaman.jumlah_pinjaman - (
            jumlah_cicilan_terbayar * angsuran_pokok
        )

        if sisa_pinjaman < 0:
            sisa_pinjaman = Decimal('0')

        # =========================
        # UPDATE STATUS OTOMATIS
        # =========================
        if sisa_pinjaman == 0:
            status = 'Lunas'
        else:
            status = 'aktif'

        # simpan ke DB kalau berubah
        if pinjaman.status != status:
            pinjaman.status = status
            pinjaman.sisa_pinjaman = sisa_pinjaman
            pinjaman.save(update_fields=['status', 'sisa_pinjaman'])

        # =========================
        # HITUNG JASA (SESUAI CONTOH)
        # =========================
        if pinjaman.id_kategori_jasa.kategori_jasa.lower() == 'turunan':
            jasa_rupiah = sisa_pinjaman * (
                pinjaman.jasa_persen / 100 if pinjaman.jasa_persen else 0
            )
        else:
            jasa_rupiah = pinjaman.jumlah_pinjaman * (
                pinjaman.jasa_persen / 100 if pinjaman.jasa_persen else 0
            )

        pinjaman.jasa_rupiah = jasa_rupiah
        pinjaman.sisa_pinjaman = sisa_pinjaman

        # =========================
        # PEMBAGIAN DATA
        # =========================
        if status == 'Lunas':
            riwayat_pinjaman.append(pinjaman)
        else:
            pinjaman_aktif.append(pinjaman)

    context = {
        'anggota': anggota,
        'pinjaman_aktif': pinjaman_aktif,
        'riwayat_pinjaman': riwayat_pinjaman,
    }

    return render(request, 'detail/pinjaman_anggota.html', context)

@login_required
def detail_pinjaman(request, id_pinjaman):
    pinjaman = get_object_or_404(Pinjaman, id_pinjaman=id_pinjaman)
    anggota = pinjaman.nomor_anggota

    # =========================
    # QUERY ANGSURAN
    # =========================
    angsuran_qs = Angsuran.objects.filter(
        id_pinjaman=pinjaman
    ).order_by('-tanggal_bayar')

    # =========================
    # FILTER TANGGAL
    # =========================
    search_date = request.GET.get('search_date')
    if search_date:
        try:
            tanggal = datetime.strptime(search_date, "%Y-%m-%d").date()
            angsuran_qs = angsuran_qs.filter(tanggal_bayar=tanggal)
        except ValueError:
            pass

    # =========================
    # PAGINATION
    # =========================
    paginator = Paginator(angsuran_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    # =========================
    # SISA PINJAMAN
    # =========================
    sisa_pinjaman = pinjaman.sisa_pinjaman

    context = {
        'pinjaman': pinjaman,
        'anggota': anggota,
        'page_obj': page_obj,
        'sisa_pinjaman': sisa_pinjaman,
    }

    return render(request, 'detail/detail_pinjaman.html', context)
