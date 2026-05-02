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
import calendar

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

    # DEBUG — cek nilai parameter yang masuk
    print(f"[DEBUG] search_query: {search_query}")
    print(f"[DEBUG] sort_by: {sort_by}")

    # query anggota aktif (ORM method)
    anggotas = Anggota.objects.filter(status='aktif')

    # DEBUG — cek berapa anggota aktif ditemukan
    print(f"[DEBUG] jumlah anggota aktif: {anggotas.count()}")

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

        # DEBUG — cek per anggota
        print(f"[DEBUG] anggota: {anggota.nama}, pinjaman aktif: {pinjaman_aktif_qs.count()}")

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

@login_required
@transaction.atomic
def bayar_pinjaman(request, id_pinjaman):
    """
    Memproses pembayaran cicilan pinjaman anggota.

    Perubahan dari versi sebelumnya:
        - Pokok bisa diisi bebas (min = angsuran_per_bulan, max = sisa_pinjaman)
        - Admin memilih bulan kewajiban secara eksplisit (dropdown)
        - Tipe "jasa saja" mendukung multi-bulan (flat dari sisa pokok sekarang)
        - Acuan cicilan/bulan dikirim ke template (hanya tampil, tidak disimpan)
        - Sisa pokok ditampilkan sebagai nominal rupiah
        - Bayar di muka diperbolehkan (pilih bulan masa depan)

    Logika tunggakan:
        - Sistem TIDAK memperbolehkan lompat bulan pembayaran.
        - Jika ada tunggakan, bulan kewajiban DIKUNCI ke bulan tunggakan pertama.
        - Tidak ada tunggakan → admin pilih bulan kewajiban bebas dari dropdown.
    """

    pinjaman    = get_object_or_404(Pinjaman, id_pinjaman=id_pinjaman)
    admin_login = request.user

    angsuran_pokok  = Decimal(pinjaman.angsuran_per_bulan or 0)
    jumlah_pinjaman = Decimal(pinjaman.jumlah_pinjaman or 0)
    jasa_persen     = Decimal(pinjaman.jasa_persen or 0)
    tanggal_mulai   = pinjaman.tanggal_meminjam
    tenor           = pinjaman.jatuh_tempo or 36

    # ── Cicilan terbayar & sisa pokok ────────────────────────────────────────
    cicilan_terbayar = Angsuran.objects.filter(
        id_pinjaman=pinjaman, tipe_bayar="cicilan"
    ).count()

    sisa_pinjaman = max(
        jumlah_pinjaman - (cicilan_terbayar * angsuran_pokok),
        Decimal("0")
    )
    pinjaman.sisa_pinjaman = sisa_pinjaman
    pinjaman.save(update_fields=["sisa_pinjaman"])

    today = date.today()

    # ── Deteksi tunggakan ────────────────────────────────────────────────────
    def akhir_bulan_ke(n):
        """Akhir bulan ke-n dari tanggal_mulai (0-based)."""
        target = tanggal_mulai + relativedelta(months=n)
        return target.replace(day=calendar.monthrange(target.year, target.month)[1])

    bulan_sudah_jatuh_tempo = sum(
        1 for i in range(tenor)
        if akhir_bulan_ke(i) < today
    )
    bulan_seharusnya   = min(bulan_sudah_jatuh_tempo, tenor)
    bulan_nunggak      = max(bulan_seharusnya - cicilan_terbayar, 0)
    sisa_cicilan_total = max(tenor - cicilan_terbayar, 0)
    ada_tunggakan      = bulan_nunggak > 0

    # ── Daftar pilihan bulan kewajiban (untuk dropdown) ──────────────────────
    # Mulai dari cicilan berikutnya yang belum dibayar sampai akhir tenor.
    # Jika ada tunggakan → dikunci ke bulan tunggakan pertama saja.
    # Jika tidak → admin bisa pilih bulan mana saja dari sekarang s/d akhir tenor.
    #
    # Cicilan ke-(cicilan_terbayar+1) = tanggal_mulai + cicilan_terbayar bulan
    # (0-based: cicilan ke-1 = months=0, ke-2 = months=1, dst)

    def tanggal_cicilan_ke(n_0based):
        """Tanggal cicilan ke-n (0-based index dari tanggal_mulai)."""
        return tanggal_mulai + relativedelta(months=n_0based)

    pilihan_bulan = []
    for idx in range(cicilan_terbayar, tenor):
        tgl = tanggal_cicilan_ke(idx)
        pilihan_bulan.append({
            "value": idx,           # indeks 0-based, dikirim ke server
            "label": tgl.strftime("%B %Y"),
            "tanggal": tgl,
        })

    # Bulan kewajiban default:
    # - Ada tunggakan → indeks cicilan_terbayar (bulan pertama yang nunggak)
    # - Tidak ada tunggakan → indeks cicilan_terbayar (bulan berikutnya)
    bulan_kewajiban_default = cicilan_terbayar  # selalu bulan berikutnya

    # ── Acuan cicilan per bulan (untuk tampil di UI, tidak disimpan) ─────────
    def hitung_jasa(sisa):
        if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
            return sisa * (jasa_persen / 100)
        return jumlah_pinjaman * (jasa_persen / 100)

    jasa_bulan_ini  = hitung_jasa(sisa_pinjaman)
    acuan_per_bulan = angsuran_pokok + jasa_bulan_ini  # hanya referensi UI

    # ── Total bayar default untuk form ──────────────────────────────────────
    # Default: 1 bulan cicilan normal
    total_bayar_default = acuan_per_bulan if sisa_pinjaman > 0 else Decimal("0")

    # ── POST ─────────────────────────────────────────────────────────────────
    if request.method == "POST":

        tipe_bayar      = request.POST.get("tipe_bayar")
        nominal_raw     = request.POST.get("nominal", "0")
        bulan_idx_str   = request.POST.get("bulan_kewajiban")   # indeks 0-based
        jumlah_bln_jasa = int(request.POST.get("jumlah_bulan_jasa", 1) or 1)

        try:
            nominal = Decimal(
                nominal_raw.replace("Rp", "").replace(".", "").replace(",", "").strip()
            )
        except Exception:
            messages.error(request, "Nominal tidak valid.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        try:
            bulan_kewajiban_idx = int(bulan_idx_str)
        except (TypeError, ValueError):
            messages.error(request, "Pilihan bulan tidak valid.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        # Validasi: tidak boleh lompat bulan
        # Bulan kewajiban minimal = cicilan_terbayar (bulan berikutnya)
        if bulan_kewajiban_idx < cicilan_terbayar:
            messages.error(request, "Bulan kewajiban tidak valid (sudah terbayar).")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        # Jika ada tunggakan, kunci ke bulan tunggakan pertama
        if ada_tunggakan and bulan_kewajiban_idx != cicilan_terbayar:
            messages.error(request, "Terdapat tunggakan. Harus lunasi tunggakan terlebih dahulu.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        tanggal_input_str = request.POST.get("tanggal")
        if not tanggal_input_str:
            messages.error(request, "Tanggal wajib diisi.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)
        tanggal_input = datetime.strptime(tanggal_input_str, "%Y-%m-%d").date()

        # Tanggal kewajiban (untuk record angsuran) = tanggal cicilan sesuai indeks
        tanggal_kewajiban = tanggal_cicilan_ke(bulan_kewajiban_idx)

        # ── Tipe cicilan ─────────────────────────────────────────────────────
        if tipe_bayar == "cicilan":

            # Pokok dari input user (bebas, min=angsuran_per_bulan, max=sisa_pinjaman)
            pokok_raw = request.POST.get("nominal_pokok", "")
            try:
                pokok_dibayar = Decimal(
                    pokok_raw.replace("Rp", "").replace(".", "").replace(",", "").strip()
                )
            except Exception:
                pokok_dibayar = angsuran_pokok

            # Validasi pokok
            if pokok_dibayar < angsuran_pokok:
                messages.error(
                    request,
                    f"Pokok minimal Rp {angsuran_pokok:,.0f} (angsuran normal per bulan)."
                )
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            if pokok_dibayar > sisa_pinjaman:
                pokok_dibayar = sisa_pinjaman  # cap ke sisa pokok

            # Jasa dihitung dari sisa pokok sebelum pembayaran ini
            jasa_cicilan = hitung_jasa(sisa_pinjaman)
            total_wajib  = pokok_dibayar + jasa_cicilan

            if nominal < total_wajib:
                messages.error(
                    request,
                    f"Nominal kurang. Minimal Rp {total_wajib:,.0f} "
                    f"(pokok Rp {pokok_dibayar:,.0f} + jasa Rp {jasa_cicilan:,.0f})."
                )
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            # Simpan angsuran — tanggal_bayar = tanggal transaksi (input user)
            #                   tanggal kewajiban tersimpan di bulan_ke (bisa di-extend model jika perlu)
            Angsuran.objects.create(
                id_pinjaman   = pinjaman,
                id_admin      = admin_login,
                tanggal_bayar = tanggal_kewajiban,   # tanggal kewajiban bulan tsb
                jumlah_bayar  = pokok_dibayar + jasa_cicilan,
                tipe_bayar    = "cicilan",
            )

            pinjaman.sisa_pinjaman = max(sisa_pinjaman - pokok_dibayar, Decimal("0"))

            # Kelebihan → simpanan sukarela
            kelebihan = nominal - total_wajib
            if kelebihan > 0:
                jenis = JenisSimpanan.objects.get(nama_jenis__iexact="SUKARELA")
                Simpanan.objects.create(
                    anggota         = pinjaman.nomor_anggota,
                    admin           = admin_login,
                    jenis_simpanan  = jenis,
                    tanggal         = tanggal_input,
                    jumlah          = kelebihan,
                    sumber_pinjaman = pinjaman,
                )

        # ── Tipe jasa saja (multi-bulan, flat) ──────────────────────────────
        elif tipe_bayar == "jasa":

            if jumlah_bln_jasa < 1:
                jumlah_bln_jasa = 1

            jasa_per_bulan = hitung_jasa(sisa_pinjaman)   # flat dari sisa pokok sekarang
            total_jasa     = jasa_per_bulan * jumlah_bln_jasa

            if nominal > total_jasa:
                messages.error(
                    request,
                    f"Nominal jasa tidak boleh melebihi Rp {total_jasa:,.0f} "
                    f"({jumlah_bln_jasa} bulan × Rp {jasa_per_bulan:,.0f})."
                )
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            # Simpan satu record per bulan jasa
            for i in range(jumlah_bln_jasa):
                tgl_jasa = tanggal_cicilan_ke(bulan_kewajiban_idx + i)
                Angsuran.objects.create(
                    id_pinjaman   = pinjaman,
                    id_admin      = admin_login,
                    tanggal_bayar = tgl_jasa,
                    jumlah_bayar  = jasa_per_bulan,
                    tipe_bayar    = "jasa",
                )

        # ── Update status ────────────────────────────────────────────────────
        if pinjaman.sisa_pinjaman <= 0:
            pinjaman.status = "Lunas"
        pinjaman.save()

        messages.success(request, "Pembayaran berhasil disimpan.")
        return redirect("pinjaman:pinjaman_list")

    # ── GET: render form ─────────────────────────────────────────────────────
    return render(request, "form/bayar_pinjaman.html", {
        "pinjaman"                : pinjaman,
        "angsuran_pokok"          : angsuran_pokok,
        "jasa_bulan_ini"          : jasa_bulan_ini,
        "acuan_per_bulan"         : acuan_per_bulan,       # referensi UI saja
        "sisa_pokok_nominal"      : sisa_pinjaman,         # ganti "X bulan" → nominal
        "sisa_cicilan_total"      : sisa_cicilan_total,
        "bulan_nunggak"           : bulan_nunggak,
        "ada_tunggakan"           : ada_tunggakan,
        "pilihan_bulan"           : pilihan_bulan,         # dropdown bulan kewajiban
        "bulan_kewajiban_default" : bulan_kewajiban_default,
        "total_bayar_default"     : total_bayar_default,
        "jasa_persen"             : jasa_persen,
    })




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