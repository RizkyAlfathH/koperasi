from datetime import datetime, date
from decimal import Decimal, InvalidOperation

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
from simpanan.models import Simpanan, JenisSimpanan
from admin_koperasi.utils import has_page_permission

@login_required
def pinjaman_list(request):
    if not has_page_permission(request.user, "pinjaman"):
        return redirect("dashboard")
    data_list = []

    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'nomor')

    anggotas = Anggota.objects.filter(status='aktif')

    if search_query:
        anggotas = anggotas.filter(
            Q(nama__icontains=search_query) |
            Q(nomor_anggota__icontains=search_query)
        )

    admin_login = request.user  # 🔥 TAMBAHAN

    for anggota in anggotas:

        # 🔥 AUTO BAYAR DARI SUKARELA KE PINJAMAN
        pinjaman_aktif_qs = Pinjaman.objects.filter(
            nomor_anggota=anggota,
            status='aktif'
        )

        for pinjaman in pinjaman_aktif_qs:
            cek_auto_sukarela_ke_pinjaman(pinjaman, admin_login)

        # =============================
        # HITUNG TOTAL PINJAMAN
        # =============================
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
    page_obj = paginator.get_page(request.GET.get('page_pinjaman'))

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

                # tambahkan sisa pinjaman lama ke pinjaman baru
                pinjaman_baru.jumlah_pinjaman += total_sisa
                pinjaman_baru.sisa_pinjaman = pinjaman_baru.jumlah_pinjaman

                # pinjaman lama dianggap selesai / digabung
                pinjaman_lama.update(
                    status='digabung',
                    sisa_pinjaman=0
                )

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

    admin_login = request.user  # 🔥 TAMBAHAN

    for pinjaman in pinjaman_qs:

        # 🔥 AUTO BAYAR DARI SUKARELA KE PINJAMAN
        cek_auto_sukarela_ke_pinjaman(pinjaman, admin_login)

        angsuran_pokok = pinjaman.angsuran_per_bulan or Decimal('0')

        jumlah_cicilan = Angsuran.objects.filter(
            id_pinjaman=pinjaman,
            tipe_bayar='cicilan'
        ).count()

        sisa_pinjaman = pinjaman.jumlah_pinjaman - (
            jumlah_cicilan * angsuran_pokok
        )

        if sisa_pinjaman < 0:
            sisa_pinjaman = Decimal('0')

        # ===== STATUS AMAN =====
        if pinjaman.status == "digabung":
            status = "digabung"

        elif sisa_pinjaman <= 0:
            status = "Lunas"

        else:
            status = "aktif"

        # UPDATE DATABASE HANYA JIKA BUKAN DIGABUNG
        if pinjaman.status != status and pinjaman.status != "digabung":
            pinjaman.status = status
            pinjaman.sisa_pinjaman = sisa_pinjaman
            pinjaman.save(update_fields=['status', 'sisa_pinjaman'])

        # ===== HITUNG JASA =====
        if status == "digabung":
            jasa_rupiah = Decimal("0")

        elif pinjaman.id_kategori_jasa.kategori_jasa.lower() == 'turunan':
            jasa_rupiah = sisa_pinjaman * (
                pinjaman.jasa_persen / 100 if pinjaman.jasa_persen else 0
            )

        else:
            jasa_rupiah = pinjaman.jumlah_pinjaman * (
                pinjaman.jasa_persen / 100 if pinjaman.jasa_persen else 0
            )

        pinjaman.jasa_rupiah = jasa_rupiah
        pinjaman.sisa_pinjaman = sisa_pinjaman

        if status in ["Lunas", "digabung"]:
            riwayat_pinjaman.append(pinjaman)
        else:
            pinjaman_aktif.append(pinjaman)

    context = {
        'anggota': anggota,
        'pinjaman_aktif': pinjaman_aktif,
        'riwayat_pinjaman': riwayat_pinjaman,
    }

    return render(
        request,
        'detail/pinjaman_anggota.html',
        context
    )

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
    tanggal_param = request.GET.get('tanggal')
    if tanggal_param:
        try:
            tanggal = datetime.strptime(tanggal_param, "%Y-%m-%d").date()
            angsuran_qs = angsuran_qs.filter(tanggal_bayar=tanggal)
        except ValueError:
            pass

    # =========================
    # PAGINATION
    # =========================
    paginator = Paginator(angsuran_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page_angsuran'))

    # =========================
    # HITUNG JASA (DINAMIS)
    # =========================
    jasa_persen = pinjaman.jasa_persen or Decimal('0')

    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == 'turunan':
        jumlah_jasa = pinjaman.sisa_pinjaman * (jasa_persen / 100)
    else:
        jumlah_jasa = pinjaman.jumlah_pinjaman * (jasa_persen / 100)

    context = {
        'pinjaman': pinjaman,
        'anggota': anggota,
        'page_obj': page_obj,
        'sisa_pinjaman': pinjaman.sisa_pinjaman,
        'jumlah_jasa': round(jumlah_jasa, 2),
    }

    return render(request, 'detail/detail_pinjaman.html', context)

@login_required
@transaction.atomic
def bayar_pinjaman(request, id_pinjaman):
    pinjaman = get_object_or_404(Pinjaman, id_pinjaman=id_pinjaman)
    admin_login = request.user

    angsuran_pokok = Decimal(pinjaman.angsuran_per_bulan or 0)
    jumlah_pinjaman = Decimal(pinjaman.jumlah_pinjaman or 0)
    jasa_persen = Decimal(pinjaman.jasa_persen or 0)

    cicilan_terbayar = Angsuran.objects.filter(
        id_pinjaman=pinjaman, tipe_bayar="cicilan"
    ).count()

    sisa_pinjaman = jumlah_pinjaman - (cicilan_terbayar * angsuran_pokok)
    sisa_pinjaman = max(sisa_pinjaman, Decimal("0"))

    pinjaman.sisa_pinjaman = sisa_pinjaman
    pinjaman.save(update_fields=["sisa_pinjaman"])

    sisa_bulan = max(pinjaman.jatuh_tempo - cicilan_terbayar, 0)

    # Hitung jasa bulan ini
    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
        jasa_rupiah = sisa_pinjaman * (jasa_persen / 100)
    else:
        jasa_rupiah = jumlah_pinjaman * (jasa_persen / 100)

    total_bayar = angsuran_pokok + jasa_rupiah

    if request.method == "POST":
        tanggal = request.POST.get("tanggal")
        tipe_bayar = request.POST.get("tipe_bayar")
        bulan = int(request.POST.get("bulan", 1))
        nominal_raw = request.POST.get("nominal")

        try:
            nominal = Decimal(
                nominal_raw.replace("Rp", "").replace(".", "").replace(",", "").strip()
            )

        except:
            messages.error(request, "Nominal tidak valid.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        if not tanggal:
            messages.error(request, "Tanggal wajib diisi.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        if tipe_bayar == "cicilan":
            # HANYA hitung minimal 1 bulan
            minimal = angsuran_pokok + jasa_rupiah

            if nominal < minimal:
                messages.error(request, f"Minimal bayar Rp {minimal:,.0f}")
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            # 1️⃣ BAYAR BULAN INI SAJA
            Angsuran.objects.create(
                id_pinjaman=pinjaman,
                id_admin=admin_login,
                tanggal_bayar=tanggal,
                jumlah_bayar=minimal,
                tipe_bayar="cicilan"
            )

            pinjaman.sisa_pinjaman -= angsuran_pokok
            pinjaman.save(update_fields=["sisa_pinjaman"])

            # 2️⃣ SISANYA MASUK SUKARELA
            kelebihan = nominal - minimal
            if kelebihan > 0:
                jenis = JenisSimpanan.objects.get(nama_jenis__iexact="SUKARELA")
                Simpanan.objects.create(
                    anggota=pinjaman.nomor_anggota,
                    admin=admin_login,
                    jenis_simpanan=jenis,
                    tanggal=tanggal,
                    jumlah=kelebihan,
                    sumber_pinjaman=pinjaman
                )

        # JASA SAJA
        elif tipe_bayar == "jasa":
            if nominal > jasa_rupiah:
                messages.error(request, "Bayar jasa tidak boleh melebihi nilai jasa.")
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            Angsuran.objects.create(
                id_pinjaman=pinjaman,
                id_admin=admin_login,
                tanggal_bayar=tanggal,
                jumlah_bayar=nominal,
                tipe_bayar="jasa"
            )

        # UPDATE STATUS
        jumlah_cicilan = Angsuran.objects.filter(
            id_pinjaman=pinjaman,
            tipe_bayar="cicilan"
        ).count()

        total_pokok_terbayar = jumlah_cicilan * angsuran_pokok

        sisa_akhir = jumlah_pinjaman - total_pokok_terbayar
        sisa_akhir = max(sisa_akhir, Decimal("0"))

        pinjaman.sisa_pinjaman = sisa_akhir

        if sisa_akhir <= 0:
            pinjaman.status = "Lunas"

        pinjaman.save()

        messages.success(request, "Pembayaran berhasil dicimpan.")
        return redirect("pinjaman:pinjaman_list")

    return render(request, "form/bayar_pinjaman.html", {
        "pinjaman": pinjaman,
        "angsuran_pokok": angsuran_pokok,
        "jasa_rupiah": jasa_rupiah,
        "total_bayar": total_bayar,
        "sisa_bulan": sisa_bulan,
    })

def cek_auto_sukarela_ke_pinjaman(pinjaman, admin_login):
    today = date.today()
    bulan_ini = today.month
    tahun_ini = today.year

    # ❌ Jangan auto bayar di bulan yang sama saat pinjaman dibuat
    if (
        pinjaman.tanggal_meminjam.month == bulan_ini and
        pinjaman.tanggal_meminjam.year == tahun_ini
    ):
        return

    # ❌ Stop kalau sudah lunas
    if pinjaman.status.lower() == "lunas":
        return

    angsuran_pokok = Decimal(pinjaman.angsuran_per_bulan or 0)
    jasa_persen = Decimal(pinjaman.jasa_persen or 0)

    # =========================
    # HITUNG SISA PINJAMAN
    # =========================
    cicilan_terbayar = Angsuran.objects.filter(
        id_pinjaman=pinjaman,
        tipe_bayar="cicilan"
    ).count()

    sisa_pinjaman = Decimal(pinjaman.jumlah_pinjaman) - (
        cicilan_terbayar * angsuran_pokok
    )

    if sisa_pinjaman <= 0:
        pinjaman.status = "Lunas"
        pinjaman.sisa_pinjaman = 0
        pinjaman.save()
        return

    # =========================
    # HITUNG JASA BULAN INI
    # =========================
    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
        jasa_rupiah = sisa_pinjaman * (jasa_persen / Decimal("100"))
    else:
        jasa_rupiah = Decimal(pinjaman.jumlah_pinjaman) * (jasa_persen / Decimal("100"))

    total_bulan_ini = angsuran_pokok + jasa_rupiah

    # =========================
    # CEK: SUDAH BAYAR BULAN INI?
    # =========================
    if Angsuran.objects.filter(
        id_pinjaman=pinjaman,
        tanggal_bayar__month=bulan_ini,
        tanggal_bayar__year=tahun_ini,
        tipe_bayar="cicilan"
    ).exists():
        return

    # =========================
    # AMBIL SALDO SUKARELA
    # =========================
    saldo_sukarela = Simpanan.objects.filter(
        anggota=pinjaman.nomor_anggota,
        jenis_simpanan__nama_jenis__iexact="SUKARELA",
        sumber_pinjaman=pinjaman
    ).aggregate(total=Sum("jumlah"))["total"] or Decimal("0")

    # ❌ Kalau saldo tidak cukup → skip
    if saldo_sukarela < total_bulan_ini:
        return

    # =========================
    # POTONG SUKARELA (HANYA 1 BULAN)
    # =========================
    jenis_sukarela, _ = JenisSimpanan.objects.get_or_create(
        nama_jenis="SUKARELA"
    )

    Simpanan.objects.create(
        anggota=pinjaman.nomor_anggota,
        admin=admin_login,
        jenis_simpanan=jenis_sukarela,
        tanggal=today,
        jumlah=-total_bulan_ini,
        sumber_pinjaman=pinjaman
    )

    # =========================
    # CATAT CICILAN BULAN INI SAJA
    # =========================
    Angsuran.objects.create(
        id_pinjaman=pinjaman,
        id_admin=admin_login,
        tanggal_bayar=today,
        jumlah_bayar=total_bulan_ini,
        tipe_bayar="cicilan"
    )

    # =========================
    # UPDATE SISA PINJAMAN
    # =========================
    pinjaman.sisa_pinjaman = sisa_pinjaman - angsuran_pokok
    if pinjaman.sisa_pinjaman <= 0:
        pinjaman.status = "Lunas"
        pinjaman.sisa_pinjaman = 0

    pinjaman.save()

def detail_pembayaran(request, pembayaran_id):
    pembayaran = get_object_or_404(Angsuran, id_pembayaran=pembayaran_id)
    pinjaman = pembayaran.id_pinjaman
    angsuran_pokok = pinjaman.angsuran_per_bulan or Decimal("0")

    # Semua angsuran untuk pinjaman ini (urut dari awal)
    semua_angsuran = Angsuran.objects.filter(
        id_pinjaman=pinjaman
    ).order_by('tanggal_bayar', 'id_pembayaran')

    # Hitung sisa sebelum & sesudah
    sisa_pinjaman = pinjaman.jumlah_pinjaman
    sisa_sebelum = sisa_pinjaman
    sisa_setelah = sisa_pinjaman

    for angsuran in semua_angsuran:
        if angsuran.id_pembayaran == pembayaran.id_pembayaran:
            sisa_sebelum = sisa_pinjaman
            if angsuran.tipe_bayar == "cicilan":
                sisa_pinjaman -= angsuran_pokok
            sisa_setelah = sisa_pinjaman
            break
        else:
            if angsuran.tipe_bayar == "cicilan":
                sisa_pinjaman -= angsuran_pokok

    sisa_sebelum = max(sisa_sebelum, Decimal("0"))
    sisa_setelah = max(sisa_setelah, Decimal("0"))

    # Hitung jasa
    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
        jasa_rupiah = sisa_sebelum * (pinjaman.jasa_persen / 100 if pinjaman.jasa_persen else 0)
    else:
        jasa_rupiah = pinjaman.jumlah_pinjaman * (pinjaman.jasa_persen / 100 if pinjaman.jasa_persen else 0)

    # Jumlah dibayar
    if pembayaran.tipe_bayar == "jasa":
        jumlah_pembayaran = pembayaran.jumlah_bayar
    else:
        jumlah_pembayaran = angsuran_pokok + jasa_rupiah

    return render(request, 'detail/detail_pembayaran.html', {
        'pembayaran': pembayaran,
        'sisa_sebelum': sisa_sebelum,
        'sisa_setelah': sisa_setelah,
        'jasa_rupiah': jasa_rupiah,
        'jumlah_pembayaran': jumlah_pembayaran,
    })