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

# fungsi view untuk pembayaran pinjaman
@login_required
@transaction.atomic
def bayar_pinjaman(request, id_pinjaman):
    """
    Memproses pembayaran cicilan pinjaman anggota.

    Catatan Penting (logika tunggakan):
        - Sistem TIDAK memperbolehkan lompat bulan pembayaran.
        - Jika anggota terakhir bayar April dan baru bayar lagi September,
          maka bulan Mei s/d September dianggap tunggakan dan harus dibayar urut.
        - Semua tanggal cicilan tunggakan dihitung OTOMATIS dari server:
            cicilan ke-i → tanggal_mulai + relativedelta(months = cicilan_terbayar + i)
          Tidak ada input tanggal dari user saat ada tunggakan.
        - Input tanggal dari user HANYA dipakai saat tidak ada tunggakan
          (bayar normal 1 bulan ke depan / bulan berjalan).
        - Input tanggal dari user juga dipakai untuk tipe "jasa saja".
        - Jumlah bulan yang dibayar DIKUNCI = jumlah tunggakan.
    """

    pinjaman    = get_object_or_404(Pinjaman, id_pinjaman=id_pinjaman)
    admin_login = request.user

    angsuran_pokok  = Decimal(pinjaman.angsuran_per_bulan or 0)
    jumlah_pinjaman = Decimal(pinjaman.jumlah_pinjaman or 0)
    jasa_persen     = Decimal(pinjaman.jasa_persen or 0)

    # hitung cicilan yang sudah dibayar (tipe cicilan saja)
    cicilan_terbayar = Angsuran.objects.filter(
        id_pinjaman=pinjaman, tipe_bayar="cicilan"
    ).count()

    # hitung sisa pinjaman
    sisa_pinjaman = max(
        jumlah_pinjaman - (cicilan_terbayar * angsuran_pokok),
        Decimal("0")
    )
    pinjaman.sisa_pinjaman = sisa_pinjaman
    pinjaman.save(update_fields=["sisa_pinjaman"])

    today         = date.today()
    tanggal_mulai = pinjaman.tanggal_meminjam
    tenor         = pinjaman.jatuh_tempo or 36  # field di model adalah jatuh_tempo

    # ── Hitung bulan yang sudah melewati jatuh tempo ────────────────────────
    # Jatuh tempo cicilan ke-N = akhir bulan ke-(N-1) dari tanggal_mulai.
    # Cicilan ke-1 jatuh tempo akhir bulan pertama (bulan yang sama dg pinjam).
    # Cicilan dianggap NUNGGAK hanya jika today sudah MELEWATI akhir bulan tsb.
    # Contoh: pinjam 1 April, today = 15 April → cicilan ke-1 belum lewat → bukan tunggakan.
    #         pinjam 1 April, today = 1 Mei   → cicilan ke-1 sudah lewat  → tunggakan.
    #
    # Rumus: hitung berapa cicilan yang jatuh temponya sudah lewat hari ini.
    # Jatuh tempo cicilan ke-N = akhir bulan (tanggal_mulai + (N-1) bulan).
    # → sama dengan: akhir bulan (tanggal_mulai + bulan_index bulan),
    #   di mana bulan_index = 0 untuk cicilan ke-1, 1 untuk cicilan ke-2, dst.
    # Cicilan ke-(bulan_index+1) sudah lewat jika today > akhir_bulan(bulan_index).

    def akhir_bulan_ke(n):
        """Tanggal akhir bulan ke-n dari tanggal_mulai (0-based index cicilan)."""
        target = tanggal_mulai + relativedelta(months=n)
        return target.replace(day=calendar.monthrange(target.year, target.month)[1])

    # Hitung berapa cicilan yang jatuh temponya sudah lewat hari ini
    # (yaitu akhir bulannya < today, bukan <=, karena hari jatuh tempo masih bisa bayar)
    bulan_sudah_jatuh_tempo = sum(
        1 for i in range(tenor)
        if akhir_bulan_ke(i) < today
    )
    # batasi agar tidak melebihi tenor
    bulan_seharusnya   = min(bulan_sudah_jatuh_tempo, tenor)
    bulan_nunggak      = max(bulan_seharusnya - cicilan_terbayar, 0)
    sisa_cicilan_total = max(tenor - cicilan_terbayar, 0)

    ada_tunggakan      = bulan_nunggak > 0
    jumlah_bulan_bayar = bulan_nunggak if ada_tunggakan else 1

    # cicilan_terbayar = indeks bulan berikutnya yang harus dibayar
    # Contoh: sudah bayar 4 cicilan (s/d Apr) → tunggakan pertama = akhir Mei
    if ada_tunggakan:
        # cicilan ke-1 → bulan ke-1 dari tanggal_mulai (bukan bulan ke-0)
        tanggal_cicilan_pertama = tanggal_mulai + relativedelta(months=cicilan_terbayar + 1)
    else:
        tanggal_cicilan_pertama = None  # pakai input user saat bayar normal

    # ── Hitung total bayar untuk form ────────────────────────────────────────
    def hitung_total_cicilan(bulan, sisa_awal):
        total = Decimal("0")
        temp  = sisa_awal
        for _ in range(bulan):
            if temp <= 0:
                break
            jasa = (
                temp * (jasa_persen / 100)
                if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan"
                else jumlah_pinjaman * (jasa_persen / 100)
            )
            total += angsuran_pokok + jasa
            temp  -= angsuran_pokok
        return total

    total_bayar = hitung_total_cicilan(jumlah_bulan_bayar, sisa_pinjaman)

    # ── POST ─────────────────────────────────────────────────────────────────
    if request.method == "POST":

        tipe_bayar  = request.POST.get("tipe_bayar")
        nominal_raw = request.POST.get("nominal")

        try:
            nominal = Decimal(
                nominal_raw.replace("Rp", "").replace(".", "").replace(",", "").strip()
            )
        except Exception:
            messages.error(request, "Nominal tidak valid.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        # ── Tipe cicilan ─────────────────────────────────────────────────────
        if tipe_bayar == "cicilan":

            bulan_bayar_final = jumlah_bulan_bayar
            total_wajib       = hitung_total_cicilan(bulan_bayar_final, sisa_pinjaman)

            if nominal < total_wajib:
                messages.error(
                    request,
                    f"Minimal bayar Rp {total_wajib:,.0f} "
                    f"({'lunasi tunggakan ' + str(bulan_bayar_final) + ' bulan' if ada_tunggakan else '1 bulan cicilan'})"
                )
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            # Parsing tanggal input user — hanya dipakai saat tidak ada tunggakan
            tanggal_user = None
            if not ada_tunggakan:
                tanggal_input_str = request.POST.get("tanggal")
                if not tanggal_input_str:
                    messages.error(request, "Tanggal wajib diisi.")
                    return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)
                tanggal_user = datetime.strptime(tanggal_input_str, "%Y-%m-%d").date()

            temp_sisa = pinjaman.sisa_pinjaman

            for i in range(bulan_bayar_final):

                if temp_sisa <= 0:
                    break

                bulan_ke = cicilan_terbayar + i  # indeks 0-based

                # ── Tanggal per cicilan ──────────────────────────────────────
                # Ada tunggakan → semua tanggal otomatis urut dari server
                # Tidak ada tunggakan → tanggal dari input user
                if ada_tunggakan:
                    # bulan_ke = cicilan_terbayar + i
                    # cicilan pertama (i=0, cicilan_terbayar=0) → +1 bulan dari tanggal_mulai
                    tanggal_bayar_real = tanggal_mulai + relativedelta(months=bulan_ke + 1)
                else:
                    tanggal_bayar_real = tanggal_user

                # hitung jasa per cicilan
                jasa = (
                    temp_sisa * (jasa_persen / 100)
                    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan"
                    else jumlah_pinjaman * (jasa_persen / 100)
                )

                Angsuran.objects.create(
                    id_pinjaman   = pinjaman,
                    id_admin      = admin_login,
                    tanggal_bayar = tanggal_bayar_real,
                    jumlah_bayar  = angsuran_pokok + jasa,
                    tipe_bayar    = "cicilan",
                )

                temp_sisa              -= angsuran_pokok
                pinjaman.sisa_pinjaman -= angsuran_pokok

            pinjaman.sisa_pinjaman = max(pinjaman.sisa_pinjaman, Decimal("0"))

            # kelebihan → simpanan sukarela
            kelebihan = nominal - total_wajib
            if kelebihan > 0:
                jenis = JenisSimpanan.objects.get(nama_jenis__iexact="SUKARELA")
                Simpanan.objects.create(
                    anggota         = pinjaman.nomor_anggota,
                    admin           = admin_login,
                    jenis_simpanan  = jenis,
                    tanggal         = today,
                    jumlah          = kelebihan,
                    sumber_pinjaman = pinjaman,
                )

        # ── Tipe jasa saja ───────────────────────────────────────────────────
        elif tipe_bayar == "jasa":

            # tanggal input selalu dipakai untuk jasa
            tanggal_input_str = request.POST.get("tanggal")
            if not tanggal_input_str:
                messages.error(request, "Tanggal wajib diisi.")
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)
            tanggal_input = datetime.strptime(tanggal_input_str, "%Y-%m-%d").date()

            jasa_rupiah = (
                pinjaman.sisa_pinjaman * (jasa_persen / 100)
                if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan"
                else jumlah_pinjaman * (jasa_persen / 100)
            )

            if nominal > jasa_rupiah:
                messages.error(request, "Bayar jasa tidak boleh melebihi nilai jasa.")
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            Angsuran.objects.create(
                id_pinjaman   = pinjaman,
                id_admin      = admin_login,
                tanggal_bayar = tanggal_input,
                jumlah_bayar  = nominal,
                tipe_bayar    = "jasa",
            )

        # update status
        if pinjaman.sisa_pinjaman <= 0:
            pinjaman.status = "Lunas"
        pinjaman.save()

        messages.success(request, "Pembayaran berhasil disimpan.")
        return redirect("pinjaman:pinjaman_list")

    # ── GET: render form ─────────────────────────────────────────────────────
    return render(request, "form/bayar_pinjaman.html", {
        "pinjaman"               : pinjaman,
        "angsuran_pokok"         : angsuran_pokok,
        "sisa_bulan"             : sisa_cicilan_total,
        "bulan_nunggak"          : bulan_nunggak,
        "ada_tunggakan"          : ada_tunggakan,
        "jumlah_bulan_bayar"     : jumlah_bulan_bayar,
        "total_bayar"            : total_bayar,
        # tanggal cicilan pertama yg tertunggak (None jika tidak ada tunggakan)
        "tanggal_cicilan_pertama": tanggal_cicilan_pertama,
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