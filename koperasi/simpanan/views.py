from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime
from .utils import hitung_saldo

from .models import Penarikan, Simpanan, JenisSimpanan, HistoryTabungan, Anggota
from django.core.paginator import Paginator
from .forms import SimpananForm, PenarikanForm


@login_required
def daftar_simpanan(request):
    data_list = []

    # 🔑 AMBIL PARAM GET (KONSISTEN)
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'nomor')

    # 🔍 BASE QUERY
    anggotas = Anggota.objects.filter(status__iexact='aktif')

    # 🔍 SEARCH
    if search_query:
        anggotas = anggotas.filter(
            Q(nama__icontains=search_query) |
            Q(nomor_anggota__icontains=search_query)
        )

    # 🔁 LOOP DATA
    for anggota in anggotas:

        def get_saldo(jenis_id):
            return (
                Simpanan.objects.filter(
                    anggota=anggota,
                    jenis_simpanan_id=jenis_id
                ).aggregate(total=Sum('jumlah'))['total'] or 0
            )

        total_pokok = get_saldo(1)
        total_wajib = get_saldo(2)
        total_sukarela = get_saldo(3)

        total_dana_sosial = (
            Simpanan.objects.filter(anggota=anggota)
            .aggregate(total=Sum('dana_sosial'))['total'] or 0
        )

        data_list.append({
            'nomor_anggota': anggota.nomor_anggota,
            'nama_anggota': anggota.nama,
            'total_pokok': total_pokok,
            'total_wajib': total_wajib,
            'total_sukarela': total_sukarela,
            'total_dana_sosial': total_dana_sosial,
        })

    # 🔃 SORTING
    if sort_by == 'nama':
        data_list.sort(key=lambda x: x['nama_anggota'])
    else:
        data_list.sort(key=lambda x: x['nomor_anggota'])

    # 📄 PAGINATION
    paginator = Paginator(data_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, "daftar_simpanan.html", {
        'data': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    })

@login_required
@transaction.atomic
def tambah_simpanan(request):
    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    if request.method == "POST":
        form = SimpananForm(request.POST)
        if form.is_valid():
            simpanan = form.save(commit=False)
            simpanan.admin = request.user
            simpanan.save()

            messages.success(request, "Simpanan berhasil ditambahkan")
            return redirect("simpanan:daftar_simpanan")
        else:
            print(form.errors)
    else:
        form = SimpananForm()

    return render(request, "form/simpanan_form.html", {"form": form})



@login_required
def cek_dana_sosial(request):
    anggota_id = request.GET.get('anggota')
    jenis_id = request.GET.get('jenis')
    tanggal_str = request.GET.get('tanggal')

    if not anggota_id or not jenis_id or not tanggal_str:
        return JsonResponse({'wajib': False})

    tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()

    sudah_bayar = Simpanan.objects.filter(
        anggota_id=anggota_id,
        jenis_simpanan_id=jenis_id,
        tanggal__month=tanggal.month,
        tanggal__year=tanggal.year
    ).exists()

    return JsonResponse({
        'wajib': not sudah_bayar
    })

@login_required
def simpanan_anggota(request, nomor_anggota):
    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)

    data_saldo = []

    for jenis in JenisSimpanan.objects.all():
        total_setor = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis,
            jenis_transaksi='SETOR'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        total_tarik = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis,
            jenis_transaksi='TARIK'
        ).aggregate(total=Sum('jumlah'))['total'] or 0

        saldo = total_setor - total_tarik

        last_transaksi = HistoryTabungan.objects.filter(
            anggota=anggota,
            jenis_simpanan=jenis
        ).order_by('-id').first()

        data_saldo.append({
            'jenis': jenis.get_nama_jenis_display(),
            'jenis_id': jenis.id,
            'saldo': saldo,
            'last_id': last_transaksi.id if last_transaksi else None
        })

    return render(request, "simpanan_anggota.html", {
        'username': request.user.username,
        'role': request.user.role,
        'anggota': anggota,
        'data_saldo': data_saldo,
    })

@login_required
def detail_simpanan(request, nomor_anggota, jenis_id):
    # ======================
    # Ambil anggota (PK = nomor_anggota)
    # ======================
    anggota = get_object_or_404(
        Anggota,
        nomor_anggota=nomor_anggota
    )

    jenis_simpanan = get_object_or_404(
        JenisSimpanan,
        id=jenis_id
    )

    # ======================
    # Filter tanggal (opsional)
    # ======================
    tanggal_filter = request.GET.get("tanggal")

    history = HistoryTabungan.objects.filter(
        anggota=anggota,
        jenis_simpanan=jenis_simpanan
    )

    if tanggal_filter:
        try:
            tanggal = datetime.strptime(tanggal_filter, "%Y-%m-%d").date()
            history = history.filter(tanggal=tanggal)
        except ValueError:
            pass

    # ======================
    # Hitung saldo
    # ======================
    total_setor = HistoryTabungan.objects.filter(
        anggota=anggota,
        jenis_simpanan=jenis_simpanan,
        jenis_transaksi="SETOR"
    ).aggregate(total=Sum("jumlah"))["total"] or 0

    total_tarik = HistoryTabungan.objects.filter(
        anggota=anggota,
        jenis_simpanan=jenis_simpanan,
        jenis_transaksi="TARIK"
    ).aggregate(total=Sum("jumlah"))["total"] or 0

    saldo_jenis = total_setor - total_tarik

    context = {
        # dibungkus supaya template kamu tetap kepakai
        "simpanan": {
            "anggota": anggota,
            "jenis_simpanan": jenis_simpanan,
        },
        "history": history,
        "saldo_jenis": saldo_jenis,
    }

    return render(request, "detail/detail_simpanan.html", context)

@login_required
@transaction.atomic
def tambah_penarikan(request, nomor_anggota, jenis):

    if request.user.role not in ["bendahara", "ketua"]:
        messages.error(request, "Tidak punya akses")
        return redirect("dashboard")

    anggota = get_object_or_404(Anggota, nomor_anggota=nomor_anggota)
    jenis_obj = get_object_or_404(JenisSimpanan, pk=jenis)

    saldo = hitung_saldo(anggota, jenis_obj)

    if request.method == "POST":
        form = PenarikanForm(
            request.POST,
            anggota=anggota,
            jenis_simpanan=jenis_obj
        )

        if form.is_valid():
            penarikan = form.save(commit=False)
            penarikan.anggota = anggota
            penarikan.jenis_simpanan = jenis_obj
            penarikan.admin = request.user
            penarikan.save()

            messages.success(request, "Penarikan berhasil")
            return redirect("simpanan:simpanan_anggota", nomor_anggota)

    else:
        form = PenarikanForm(
            anggota=anggota,
            jenis_simpanan=jenis_obj
        )

    return render(request, "form/penarikan_form.html", {
        "form": form,
        "anggota": anggota,
        "saldo": saldo,
    })

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