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
from dateutil.relativedelta import relativedelta

# fungsi view untuk menampilkan daftar pinjaman
@login_required
def pinjaman_list(request):

    # validasi permission (fungsi custom)
    if not has_page_permission(request.user, "pinjaman"):
        return redirect("dashboard")

    data_list = []  # list (objek) untuk menampung data

    # mengambil parameter GET
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'nomor')

    # query anggota aktif (ORM method)
    anggotas = Anggota.objects.filter(status='aktif')

    # filter pencarian (Q object untuk OR query)
    if search_query:
        anggotas = anggotas.filter(
            Q(nama__icontains=search_query) |
            Q(nomor_anggota__icontains=search_query)
        )

    admin_login = request.user  # objek user login

    # loop data anggota
    for anggota in anggotas:

        # query pinjaman aktif
        pinjaman_aktif_qs = Pinjaman.objects.filter(
            nomor_anggota=anggota,
            status='aktif'
        )

        # proses auto bayar (fungsi custom)
        for pinjaman in pinjaman_aktif_qs:
            cek_auto_sukarela_ke_pinjaman(pinjaman, admin_login)

        # fungsi lokal (nested function) untuk hitung total pinjaman
        def total_pinjaman(jenis):
            return (
                Pinjaman.objects.filter(
                    nomor_anggota=anggota,
                    id_jenis_pinjaman__nama_jenis=jenis,
                    status='aktif'
                ).aggregate(total=Sum('sisa_pinjaman'))['total'] or 0
            )

        # hitung total per jenis
        reguler = total_pinjaman('Reguler')
        khusus = total_pinjaman('Khusus')
        barang = total_pinjaman('Barang')

        total = reguler + khusus + barang

        # ambil pinjaman aktif terbaru
        pinjaman_aktif = Pinjaman.objects.filter(
            nomor_anggota=anggota,
            status='aktif'
        ).order_by('-tanggal_meminjam').first()

        # append ke list (dictionary)
        data_list.append({
            'id_pinjaman': pinjaman_aktif.id_pinjaman if pinjaman_aktif else None,
            'nomor_anggota': anggota.nomor_anggota,
            'nama': anggota.nama,
            'reguler': reguler,
            'khusus': khusus,
            'barang': barang,
            'total': total,
        })

    # sorting data (method list)
    if sort_by == 'nama':
        data_list.sort(key=lambda x: x['nama'])
    else:
        data_list.sort(key=lambda x: x['nomor_anggota'])

    # pagination (objek Paginator)
    paginator = Paginator(data_list, 10)
    page_obj = paginator.get_page(request.GET.get('page_pinjaman'))

    # render template
    return render(request, 'pinjaman_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    })


# fungsi view untuk tambah pinjaman
@login_required
@transaction.atomic
def tambah_pinjaman(request):

    user = request.user  # objek user login

    # validasi role (authorization)
    if user.role not in ['admin', 'ketua', 'bendahara']:
        messages.error(request, 'Anda tidak memiliki hak akses.')
        return redirect('pinjaman:pinjaman_list')

    # cek request POST
    if request.method == 'POST':
        form = PinjamanForm(request.POST)  # objek form

        # validasi form
        if form.is_valid():
            pinjaman_baru = form.save(commit=False)  # objek model Pinjaman

            # set admin pembuat
            pinjaman_baru.id_admin = user

            # set status awal
            pinjaman_baru.status = 'aktif'

            # set sisa pinjaman awal
            pinjaman_baru.sisa_pinjaman = pinjaman_baru.jumlah_pinjaman

            # query pinjaman lama (jenis sama & masih aktif)
            pinjaman_lama = Pinjaman.objects.filter(
                nomor_anggota=pinjaman_baru.nomor_anggota,
                id_jenis_pinjaman=pinjaman_baru.id_jenis_pinjaman,
                status='aktif'
            )

            # jika ada pinjaman lama
            if pinjaman_lama.exists():

                # aggregate total sisa pinjaman lama
                total_sisa = pinjaman_lama.aggregate(
                    total=Sum('sisa_pinjaman')
                )['total'] or Decimal('0')

                # gabungkan ke pinjaman baru
                pinjaman_baru.jumlah_pinjaman += total_sisa
                pinjaman_baru.sisa_pinjaman = pinjaman_baru.jumlah_pinjaman

                # update pinjaman lama (method ORM update)
                pinjaman_lama.update(
                    status='digabung',
                    sisa_pinjaman=0
                )

            # simpan ke database
            pinjaman_baru.save()

            messages.success(request, 'Pinjaman berhasil ditambahkan.')
            return redirect('pinjaman:pinjaman_list')

    else:
        form = PinjamanForm()  # form kosong

    # context (dictionary)
    context = {
        'form': form,
        'role': user.role,
        'username': user.username,
    }

    return render(request, 'form/pinjaman_form.html', context)

# fungsi view untuk autocomplete anggota (digunakan untuk ajax/search select)
@login_required
def autocomplete_anggota(request):

    # ambil parameter GET
    term = request.GET.get('term', '')

    # query anggota aktif + filter nama (ORM method)
    anggota_list = Anggota.objects.filter(
        nama__icontains=term,
        status='aktif'
    )[:10]  # slicing queryset (membatasi 10 data)

    # return response JSON (objek JsonResponse)
    return JsonResponse({
        "results": [
            {
                "id": a.pk,
                "text": f"{a.nomor_anggota} - {a.nama}"
            }
            for a in anggota_list  # list comprehension
        ]
    })


# fungsi view untuk melihat pinjaman per anggota
@login_required
def pinjaman_anggota(request, nomor_anggota):

    # ambil data anggota (method get_object_or_404)
    anggota = get_object_or_404(
        Anggota,
        nomor_anggota=nomor_anggota
    )

    # query pinjaman + optimasi select_related (ORM method)
    pinjaman_qs = Pinjaman.objects.filter(
        nomor_anggota=anggota
    ).select_related(
        'id_jenis_pinjaman',
        'id_kategori_jasa'
    ).order_by('tanggal_meminjam')

    pinjaman_aktif = []       # list untuk pinjaman aktif
    riwayat_pinjaman = []     # list untuk riwayat

    admin_login = request.user  # objek user login

    # loop semua pinjaman
    for pinjaman in pinjaman_qs:

        # fungsi custom auto bayar
        cek_auto_sukarela_ke_pinjaman(pinjaman, admin_login)

        # ambil angsuran per bulan
        angsuran_pokok = pinjaman.angsuran_per_bulan or Decimal('0')

        # hitung jumlah cicilan (ORM method count)
        jumlah_cicilan = Angsuran.objects.filter(
            id_pinjaman=pinjaman,
            tipe_bayar='cicilan'
        ).count()

        # hitung sisa pinjaman
        sisa_pinjaman = pinjaman.jumlah_pinjaman - (
            jumlah_cicilan * angsuran_pokok
        )

        # validasi tidak boleh negatif
        if sisa_pinjaman < 0:
            sisa_pinjaman = Decimal('0')

        # penentuan status (logika kondisi)
        if pinjaman.status == "digabung":
            status = "digabung"
        elif sisa_pinjaman <= 0:
            status = "Lunas"
        else:
            status = "aktif"

        # update database jika status berubah
        if pinjaman.status != status and pinjaman.status != "digabung":
            pinjaman.status = status
            pinjaman.sisa_pinjaman = sisa_pinjaman
            pinjaman.save(update_fields=['status', 'sisa_pinjaman'])

        # perhitungan jasa
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

        # set attribute sementara pada objek
        pinjaman.jasa_rupiah = jasa_rupiah
        pinjaman.sisa_pinjaman = sisa_pinjaman

        # pisahkan data aktif dan riwayat
        if status in ["Lunas", "digabung"]:
            riwayat_pinjaman.append(pinjaman)
        else:
            pinjaman_aktif.append(pinjaman)

    # context (dictionary)
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


# fungsi view untuk detail satu pinjaman
@login_required
def detail_pinjaman(request, id_pinjaman):

    # ambil data pinjaman
    pinjaman = get_object_or_404(Pinjaman, id_pinjaman=id_pinjaman)

    anggota = pinjaman.nomor_anggota  # relasi objek

    # query angsuran (ORM)
    angsuran_qs = Angsuran.objects.filter(
        id_pinjaman=pinjaman
    ).order_by('-tanggal_bayar')

    # filter berdasarkan tanggal (input user)
    tanggal_param = request.GET.get('tanggal')
    if tanggal_param:
        try:
            # parsing string ke date (fungsi datetime)
            tanggal = datetime.strptime(tanggal_param, "%Y-%m-%d").date()
            angsuran_qs = angsuran_qs.filter(tanggal_bayar=tanggal)
        except ValueError:
            pass  # handling jika format salah

    # pagination (class Paginator)
    paginator = Paginator(angsuran_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page_angsuran'))

    # hitung jasa
    jasa_persen = pinjaman.jasa_persen or Decimal('0')

    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == 'turunan':
        jumlah_jasa = pinjaman.sisa_pinjaman * (jasa_persen / 100)
    else:
        jumlah_jasa = pinjaman.jumlah_pinjaman * (jasa_persen / 100)

    # context
    context = {
        'pinjaman': pinjaman,
        'anggota': anggota,
        'page_obj': page_obj,
        'sisa_pinjaman': pinjaman.sisa_pinjaman,
        'jumlah_jasa': round(jumlah_jasa, 2),
    }

    return render(request, 'detail/detail_pinjaman.html', context)

# fungsi view untuk pembayaran pinjaman
@login_required
@transaction.atomic  # decorator untuk transaksi database (rollback jika gagal)
def bayar_pinjaman(request, id_pinjaman):

    # ambil data pinjaman (method ORM)
    pinjaman = get_object_or_404(Pinjaman, id_pinjaman=id_pinjaman)

    admin_login = request.user  # objek user login

    # konversi ke Decimal untuk perhitungan aman
    angsuran_pokok = Decimal(pinjaman.angsuran_per_bulan or 0)
    jumlah_pinjaman = Decimal(pinjaman.jumlah_pinjaman or 0)
    jasa_persen = Decimal(pinjaman.jasa_persen or 0)

    # hitung jumlah cicilan yang sudah dibayar (method count)
    cicilan_terbayar = Angsuran.objects.filter(
        id_pinjaman=pinjaman, tipe_bayar="cicilan"
    ).count()

    # hitung sisa pinjaman (operasi aritmatika)
    sisa_pinjaman = jumlah_pinjaman - (cicilan_terbayar * angsuran_pokok)

    # validasi agar tidak negatif
    sisa_pinjaman = max(sisa_pinjaman, Decimal("0"))

    # update field sisa_pinjaman (method save)
    pinjaman.sisa_pinjaman = sisa_pinjaman
    pinjaman.save(update_fields=["sisa_pinjaman"])

    # hitung bulan berjalan
    today = date.today()
    tanggal_mulai = pinjaman.tanggal_meminjam

    # rumus bulan berjalan
    bulan_berjalan = (today.year - tanggal_mulai.year) * 12 + (today.month - tanggal_mulai.month) + 1

    # sisa bulan yang bisa dicicil
    sisa_bulan_aktif = max(bulan_berjalan - cicilan_terbayar, 0)

    # proses jika request POST
    if request.method == "POST":

        # ambil input dari form
        tanggal_input_str = request.POST.get("tanggal")
        tipe_bayar = request.POST.get("tipe_bayar")
        bulan_input = int(request.POST.get("bulan", 1))
        nominal_raw = request.POST.get("nominal")

        # parsing nominal ke Decimal
        try:
            nominal = Decimal(
                nominal_raw.replace("Rp", "").replace(".", "").replace(",", "").strip()
            )
        except:
            messages.error(request, "Nominal tidak valid.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        # validasi tanggal
        if not tanggal_input_str:
            messages.error(request, "Tanggal wajib diisi.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        # parsing tanggal (fungsi datetime)
        tanggal_input = datetime.strptime(tanggal_input_str, "%Y-%m-%d").date()

        # jika tipe bayar cicilan
        if tipe_bayar == "cicilan":

            # validasi bulan tidak melebihi sisa
            bulan_valid = min(bulan_input, sisa_bulan_aktif)

            total_wajib = Decimal("0")
            temp_sisa = sisa_pinjaman

            # loop hitung total kewajiban
            for i in range(bulan_valid):

                if temp_sisa <= 0:
                    break

                # hitung jasa
                if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
                    jasa = temp_sisa * (jasa_persen / 100)
                else:
                    jasa = jumlah_pinjaman * (jasa_persen / 100)

                total_wajib += angsuran_pokok + jasa
                temp_sisa -= angsuran_pokok

            # validasi minimal pembayaran
            if nominal < total_wajib:
                messages.error(request, f"Minimal bayar Rp {total_wajib:,.0f}")
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            # simpan cicilan ke database
            for i in range(bulan_valid):

                if pinjaman.sisa_pinjaman <= 0:
                    break

                bulan_ke = cicilan_terbayar + i

                # logika tanggal pembayaran
                if i == 0:
                    tanggal_bayar_real = tanggal_input
                else:
                    tanggal_bayar_real = (
                        tanggal_mulai + relativedelta(months=bulan_ke)
                    ).replace(day=1)

                # hitung jasa lagi (per cicilan)
                if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
                    jasa = pinjaman.sisa_pinjaman * (jasa_persen / 100)
                else:
                    jasa = jumlah_pinjaman * (jasa_persen / 100)

                total_bayar = angsuran_pokok + jasa

                # create data angsuran (method ORM create)
                Angsuran.objects.create(
                    id_pinjaman=pinjaman,
                    id_admin=admin_login,
                    tanggal_bayar=tanggal_bayar_real,
                    jumlah_bayar=total_bayar,
                    tipe_bayar="cicilan"
                )

                # kurangi sisa pinjaman
                pinjaman.sisa_pinjaman -= angsuran_pokok

            pinjaman.sisa_pinjaman = max(pinjaman.sisa_pinjaman, Decimal("0"))

            # hitung kelebihan pembayaran
            kelebihan = nominal - total_wajib

            # jika ada kelebihan, masukkan ke simpanan sukarela
            if kelebihan > 0:
                jenis = JenisSimpanan.objects.get(nama_jenis__iexact="SUKARELA")

                Simpanan.objects.create(
                    anggota=pinjaman.nomor_anggota,
                    admin=admin_login,
                    jenis_simpanan=jenis,
                    tanggal=today,
                    jumlah=kelebihan,
                    sumber_pinjaman=pinjaman
                )

        # jika tipe bayar jasa saja
        elif tipe_bayar == "jasa":

            # hitung nilai jasa
            if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
                jasa_rupiah = pinjaman.sisa_pinjaman * (jasa_persen / 100)
            else:
                jasa_rupiah = jumlah_pinjaman * (jasa_persen / 100)

            # validasi tidak boleh lebih
            if nominal > jasa_rupiah:
                messages.error(request, "Bayar jasa tidak boleh melebihi nilai jasa.")
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            # simpan pembayaran jasa
            Angsuran.objects.create(
                id_pinjaman=pinjaman,
                id_admin=admin_login,
                tanggal_bayar=today,
                jumlah_bayar=nominal,
                tipe_bayar="jasa"
            )

        # update status pinjaman
        if pinjaman.sisa_pinjaman <= 0:
            pinjaman.status = "Lunas"

        pinjaman.save()

        messages.success(request, "Pembayaran berhasil disimpan.")
        return redirect("pinjaman:pinjaman_list")

    # render form pembayaran
    return render(request, "form/bayar_pinjaman.html", {
        "pinjaman": pinjaman,
        "angsuran_pokok": angsuran_pokok,
        "sisa_bulan": sisa_bulan_aktif,
    })

# fungsi: helper function untuk auto pembayaran dari simpanan sukarela ke pinjaman
def cek_auto_sukarela_ke_pinjaman(pinjaman, admin_login):
    # objek: mengambil tanggal hari ini
    today = date.today()
    bulan_ini = today.month
    tahun_ini = today.year

    # kondisi: tidak melakukan auto bayar jika pinjaman dibuat di bulan yang sama
    if (
        pinjaman.tanggal_meminjam.month == bulan_ini and
        pinjaman.tanggal_meminjam.year == tahun_ini
    ):
        return

    # kondisi: jika pinjaman sudah lunas maka proses dihentikan
    if pinjaman.status.lower() == "lunas":
        return

    # objek: mengambil nilai angsuran dan jasa dalam bentuk decimal
    angsuran_pokok = Decimal(pinjaman.angsuran_per_bulan or 0)
    jasa_persen = Decimal(pinjaman.jasa_persen or 0)

    # proses: menghitung jumlah cicilan yang sudah dibayar
    cicilan_terbayar = Angsuran.objects.filter(
        id_pinjaman=pinjaman,
        tipe_bayar="cicilan"
    ).count()

    # proses: menghitung sisa pinjaman
    sisa_pinjaman = Decimal(pinjaman.jumlah_pinjaman) - (
        cicilan_terbayar * angsuran_pokok
    )

    # kondisi: jika sisa pinjaman sudah habis maka update status menjadi lunas
    if sisa_pinjaman <= 0:
        pinjaman.status = "Lunas"
        pinjaman.sisa_pinjaman = 0
        pinjaman.save()
        return

    # proses: menghitung jasa berdasarkan jenis kategori jasa
    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
        jasa_rupiah = sisa_pinjaman * (jasa_persen / Decimal("100"))
    else:
        jasa_rupiah = Decimal(pinjaman.jumlah_pinjaman) * (jasa_persen / Decimal("100"))

    # proses: total pembayaran bulan ini (pokok + jasa)
    total_bulan_ini = angsuran_pokok + jasa_rupiah

    # kondisi: cek apakah sudah ada pembayaran cicilan di bulan ini
    if Angsuran.objects.filter(
        id_pinjaman=pinjaman,
        tanggal_bayar__month=bulan_ini,
        tanggal_bayar__year=tahun_ini,
        tipe_bayar="cicilan"
    ).exists():
        return

    # proses: mengambil saldo simpanan sukarela yang terkait pinjaman
    saldo_sukarela = Simpanan.objects.filter(
        anggota=pinjaman.nomor_anggota,
        jenis_simpanan__nama_jenis__iexact="SUKARELA",
        sumber_pinjaman=pinjaman
    ).aggregate(total=Sum("jumlah"))["total"] or Decimal("0")

    # kondisi: jika saldo tidak mencukupi maka tidak dilakukan auto bayar
    if saldo_sukarela < total_bulan_ini:
        return

    # objek: mengambil atau membuat jenis simpanan sukarela
    jenis_sukarela, _ = JenisSimpanan.objects.get_or_create(
        nama_jenis="SUKARELA"
    )

    # proses: mengurangi saldo sukarela (dicatat sebagai nilai negatif)
    Simpanan.objects.create(
        anggota=pinjaman.nomor_anggota,
        admin=admin_login,
        jenis_simpanan=jenis_sukarela,
        tanggal=today,
        jumlah=-total_bulan_ini,
        sumber_pinjaman=pinjaman
    )

    # proses: mencatat pembayaran cicilan bulan ini
    Angsuran.objects.create(
        id_pinjaman=pinjaman,
        id_admin=admin_login,
        tanggal_bayar=today,
        jumlah_bayar=total_bulan_ini,
        tipe_bayar="cicilan"
    )

    # proses: update sisa pinjaman setelah pembayaran
    pinjaman.sisa_pinjaman = sisa_pinjaman - angsuran_pokok

    # kondisi: jika sudah lunas setelah pembayaran
    if pinjaman.sisa_pinjaman <= 0:
        pinjaman.status = "Lunas"
        pinjaman.sisa_pinjaman = 0

    # method: menyimpan perubahan pada objek pinjaman
    pinjaman.save()


# fungsi: menampilkan detail satu transaksi pembayaran
def detail_pembayaran(request, pembayaran_id):
    # objek: mengambil data pembayaran berdasarkan id
    pembayaran = get_object_or_404(Angsuran, id_pembayaran=pembayaran_id)

    # objek: mengambil relasi pinjaman dari pembayaran
    pinjaman = pembayaran.id_pinjaman

    # objek: mengambil nilai angsuran pokok
    angsuran_pokok = pinjaman.angsuran_per_bulan or Decimal("0")

    # query: mengambil semua angsuran terkait pinjaman (diurutkan dari awal)
    semua_angsuran = Angsuran.objects.filter(
        id_pinjaman=pinjaman
    ).order_by('tanggal_bayar', 'id_pembayaran')

    # variabel: inisialisasi sisa pinjaman sebelum dan sesudah pembayaran
    sisa_pinjaman = pinjaman.jumlah_pinjaman
    sisa_sebelum = sisa_pinjaman
    sisa_setelah = sisa_pinjaman

    # loop: menghitung sisa sebelum dan sesudah pembayaran tertentu
    for angsuran in semua_angsuran:
        if angsuran.id_pembayaran == pembayaran.id_pembayaran:
            sisa_sebelum = sisa_pinjaman

            # kondisi: hanya cicilan yang mengurangi pokok
            if angsuran.tipe_bayar == "cicilan":
                sisa_pinjaman -= angsuran_pokok

            sisa_setelah = sisa_pinjaman
            break
        else:
            if angsuran.tipe_bayar == "cicilan":
                sisa_pinjaman -= angsuran_pokok

    # proses: memastikan nilai tidak negatif
    sisa_sebelum = max(sisa_sebelum, Decimal("0"))
    sisa_setelah = max(sisa_setelah, Decimal("0"))

    # proses: menghitung jasa berdasarkan kategori
    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
        jasa_rupiah = sisa_sebelum * (pinjaman.jasa_persen / 100 if pinjaman.jasa_persen else 0)
    else:
        jasa_rupiah = pinjaman.jumlah_pinjaman * (pinjaman.jasa_persen / 100 if pinjaman.jasa_persen else 0)

    # kondisi: menentukan jumlah pembayaran
    if pembayaran.tipe_bayar == "jasa":
        jumlah_pembayaran = pembayaran.jumlah_bayar
    else:
        jumlah_pembayaran = angsuran_pokok + jasa_rupiah

    # return: menampilkan ke template dengan context
    return render(request, 'detail/detail_pembayaran.html', {
        'pembayaran': pembayaran,
        'sisa_sebelum': sisa_sebelum,
        'sisa_setelah': sisa_setelah,
        'jasa_rupiah': jasa_rupiah,
        'jumlah_pembayaran': jumlah_pembayaran,
    })