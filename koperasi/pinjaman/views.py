from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Q

from .models import Angsuran, Pinjaman, KategoriJasa, JenisPinjaman
from .forms import PinjamanForm
from admin_koperasi.models import User
from anggota.models import Anggota
from simpanan.models import Simpanan, JenisSimpanan
from admin_koperasi.utils import has_page_permission
from dateutil.relativedelta import relativedelta
import calendar
import re

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

    user = request.user

    if user.role not in ['admin', 'ketua', 'bendahara']:
        messages.error(request, 'Anda tidak memiliki hak akses.')
        return redirect('pinjaman:pinjaman_list')

    if request.method == 'POST':
        anggota_id   = request.POST.get('nomor_anggota')
        tanggal_str  = request.POST.get('tanggal_meminjam')
        jumlah_baris = int(request.POST.get('jumlah_baris', 1))

        # ── Ambil objek anggota ──────────────────────────────────────────
        from anggota.models import Anggota
        try:
            anggota_obj = Anggota.objects.get(pk=anggota_id) if anggota_id else None
        except Anggota.DoesNotExist:
            anggota_obj = None

        # ── Parse tanggal ────────────────────────────────────────────────
        import datetime
        try:
            tanggal = datetime.date.fromisoformat(tanggal_str)
        except (TypeError, ValueError):
            tanggal = None

        if not anggota_obj or not tanggal:
            messages.error(request, 'Anggota dan tanggal wajib diisi.')
            form = PinjamanForm(request.POST)
            return render(request, 'form/pinjaman_form.html', {
                'form': form, 'role': user.role, 'username': user.username,
            })

        # ── Kumpulkan data tiap baris ────────────────────────────────────
        baris_list = []
        has_error  = False
        errors     = []

        for i in range(jumlah_baris):
            jenis_id     = request.POST.get(f'jenis_{i}')
            tenor_raw    = request.POST.get(f'tenor_{i}', '0')
            jumlah_raw   = request.POST.get(f'jumlah_{i}', '0')
            angsuran_raw = request.POST.get(f'angsuran_{i}', '0')
            kategori_id  = request.POST.get(f'kategori_{i}')
            persen_raw   = request.POST.get(f'jasa_persen_{i}', '0')
            jasarp_raw   = request.POST.get(f'jasa_rupiah_{i}', '0')

            try:
                tenor    = int(tenor_raw or 0)
                jumlah   = Decimal(re.sub(r'\D', '', jumlah_raw) or '0')
                angsuran = Decimal(re.sub(r'\D', '', angsuran_raw) or '0')
                persen   = Decimal(persen_raw or '0')
                jasa_rp  = Decimal(re.sub(r'\D', '', jasarp_raw) or '0')
            except Exception:
                errors.append(f'Baris {i+1}: format angka tidak valid.')
                has_error = True
                continue

            # Validasi per baris
            baris_errors = []
            if not jenis_id:
                baris_errors.append('jenis pinjaman')
            if tenor < 1 or tenor > 36:
                baris_errors.append('tenor (1-36 bulan)')
            if jumlah <= 0:
                baris_errors.append('jumlah pinjaman')
            if angsuran <= 0:
                baris_errors.append('angsuran per bulan')
            if not kategori_id:
                baris_errors.append('kategori jasa')
            if persen < 0 or persen > 100:
                baris_errors.append('persentase jasa (0-100%)')

            if baris_errors:
                errors.append(f'Baris {i+1}: wajib isi {", ".join(baris_errors)}.')
                has_error = True
                continue

            baris_list.append({
                'jenis_id'   : jenis_id,
                'tenor'      : tenor,
                'jumlah'     : jumlah,
                'angsuran'   : angsuran,
                'kategori_id': kategori_id,
                'persen'     : persen,
                'jasa_rp'    : jasa_rp,
            })

        if has_error:
            for err in errors:
                messages.error(request, err)
            form = PinjamanForm(request.POST)
            return render(request, 'form/pinjaman_form.html', {
                'form': form, 'role': user.role, 'username': user.username,
            })

        # ── Simpan tiap baris ────────────────────────────────────────────
        saved = 0
        for baris in baris_list:
            try:
                jenis    = JenisPinjaman.objects.get(pk=baris['jenis_id'])
                kategori = KategoriJasa.objects.get(pk=baris['kategori_id'])
            except Exception:
                messages.error(request, 'Jenis atau kategori tidak ditemukan.')
                continue

            pinjaman_baru = Pinjaman(
                nomor_anggota      = anggota_obj,
                id_jenis_pinjaman  = jenis,
                id_kategori_jasa   = kategori,
                id_admin           = user,
                tanggal_meminjam   = tanggal,
                jatuh_tempo        = baris['tenor'],
                jumlah_pinjaman    = baris['jumlah'],
                angsuran_per_bulan = baris['angsuran'],
                jasa_persen        = baris['persen'],
                jasa_rupiah        = baris['jasa_rp'],
                sisa_pinjaman      = baris['jumlah'],
                status             = 'Aktif',
            )

            # Cek & gabung pinjaman lama (jenis sama, masih aktif)
            pinjaman_lama = Pinjaman.objects.filter(
                nomor_anggota     = anggota_obj,
                id_jenis_pinjaman = jenis,
                status            = 'Aktif',
            )
            if pinjaman_lama.exists():
                total_sisa = pinjaman_lama.aggregate(
                    total=Sum('sisa_pinjaman')
                )['total'] or Decimal('0')

                pinjaman_baru.jumlah_pinjaman += total_sisa
                pinjaman_baru.sisa_pinjaman    = pinjaman_baru.jumlah_pinjaman

                pinjaman_lama.update(status='digabung', sisa_pinjaman=0)

            pinjaman_baru.save()
            saved += 1

        messages.success(request, f'{saved} pinjaman berhasil ditambahkan.')
        return redirect('pinjaman:pinjaman_list')

    else:
        form = PinjamanForm()

    return render(request, 'form/pinjaman_form.html', {
        'form'    : form,
        'role'    : user.role,
        'username': user.username,
    })

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


# ── HELPER: hitung sisa pinjaman dari akumulasi pokok terbayar ───────────────
def _hitung_sisa_pinjaman(pinjaman):
    """
    Menghitung sisa pinjaman berdasarkan total pokok yang sudah dibayar
    (Sum jumlah_pokok tipe 'cicilan'), bukan dari COUNT cicilan.

    Dengan cara ini, pelunasan sekaligus (bayar pokok penuh dalam 1 transaksi)
    akan langsung mencerminkan sisa = 0, tanpa perlu membuat banyak record.
    """
    total_pokok_dibayar = Angsuran.objects.filter(
        id_pinjaman=pinjaman,
        tipe_bayar='cicilan'
    ).aggregate(total=Sum('jumlah_pokok'))['total'] or Decimal('0')

    sisa = max(
        Decimal(pinjaman.jumlah_pinjaman or 0) - total_pokok_dibayar,
        Decimal('0')
    )
    return sisa


def _jasa_sudah_dibayar_bulan_ini(pinjaman, tahun, bulan):
    """
    Cek apakah jasa untuk bulan-tahun tertentu sudah dibayar.

    Jasa dianggap sudah lunas untuk suatu bulan kalender jika ada
    record Angsuran (tipe 'cicilan' ATAU 'jasa') yang tanggal_bayar-nya
    jatuh di bulan & tahun yang sama.

    Logika bisnis:
    - Cicilan = bayar pokok + jasa sekaligus → jasa bulan itu sudah terbayar
    - Jasa saja → jasa bulan itu sudah terbayar
    - Pelunasan di bulan yang sama dengan cicilan sebelumnya → jasa tidak perlu bayar lagi
    """
    return Angsuran.objects.filter(
        id_pinjaman=pinjaman,
        tipe_bayar__in=['cicilan', 'jasa'],
        tanggal_bayar__year=tahun,
        tanggal_bayar__month=bulan,
    ).exists()


def _bulan_mulai_cicilan(tanggal_meminjam):
    """
    Tenor dimulai dari bulan BERIKUTNYA setelah tanggal pinjam.

    Contoh:
    - Pinjam 24 April  → cicilan bulan ke-1 = 1 Mei
    - Pinjam 1 Januari → cicilan bulan ke-1 = 1 Februari

    Mengembalikan date dengan day=1 dari bulan pertama cicilan.
    """
    bulan_pertama = tanggal_meminjam + relativedelta(months=1)
    return bulan_pertama.replace(day=1)


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

        # ── Hitung sisa pokok berdasarkan total pokok terbayar (bukan count) ──
        sisa_pinjaman = _hitung_sisa_pinjaman(pinjaman)

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

    # hitung sisa pokok dari akumulasi (konsisten dengan bayar_pinjaman)
    sisa_pinjaman = _hitung_sisa_pinjaman(pinjaman)

    # hitung jasa
    jasa_persen = pinjaman.jasa_persen or Decimal('0')

    if pinjaman.id_kategori_jasa.kategori_jasa.lower() == 'turunan':
        jumlah_jasa = sisa_pinjaman * (jasa_persen / 100)
    else:
        jumlah_jasa = pinjaman.jumlah_pinjaman * (jasa_persen / 100)

    # context
    context = {
        'pinjaman': pinjaman,
        'anggota': anggota,
        'page_obj': page_obj,
        'sisa_pinjaman': sisa_pinjaman,
        'jumlah_jasa': round(jumlah_jasa, 2),
    }

    return render(request, 'detail/detail_pinjaman.html', context)

@login_required
@transaction.atomic
def bayar_pinjaman(request, id_pinjaman):
    pinjaman    = get_object_or_404(Pinjaman, id_pinjaman=id_pinjaman)
    admin_login = request.user

    angsuran_pokok  = Decimal(pinjaman.angsuran_per_bulan or 0)
    jumlah_pinjaman = Decimal(pinjaman.jumlah_pinjaman or 0)
    jasa_persen     = Decimal(pinjaman.jasa_persen or 0)
    tanggal_mulai   = pinjaman.tanggal_meminjam
    tenor           = pinjaman.jatuh_tempo or 36

    # ── Sisa pokok dari SUM jumlah_pokok ─────────────────────────────────
    sisa_pinjaman = _hitung_sisa_pinjaman(pinjaman)
    pinjaman.sisa_pinjaman = sisa_pinjaman
    pinjaman.save(update_fields=["sisa_pinjaman"])

    today = date.today()

    # ── Bulan mulai cicilan = bulan BERIKUTNYA dari tanggal pinjam ────────
    bulan_mulai_cicilan = (tanggal_mulai + relativedelta(months=1)).replace(day=1)

    def tanggal_cicilan_ke(n_0based):
        return bulan_mulai_cicilan + relativedelta(months=n_0based)

    def akhir_bulan(tgl):
        return tgl.replace(day=calendar.monthrange(tgl.year, tgl.month)[1])

    # ── Set bulan yang sudah ada record cicilan ───────────────────────────
    bulan_sudah_cicilan = set()
    for row in Angsuran.objects.filter(
        id_pinjaman=pinjaman, tipe_bayar="cicilan"
    ).values("tanggal_bayar"):
        tgl = row["tanggal_bayar"]
        bulan_sudah_cicilan.add((tgl.year, tgl.month))

    # ── Hitung total pokok terbayar & cicilan_terbayar ────────────────────
    cicilan_records = Angsuran.objects.filter(
        id_pinjaman=pinjaman, tipe_bayar="cicilan"
    ).order_by("tanggal_bayar", "id_pembayaran")

    total_pokok_terbayar = sum(
        r.jumlah_pokok or Decimal("0") for r in cicilan_records
    )

    if angsuran_pokok > 0:
        bulan_terpenuhi = int(total_pokok_terbayar / angsuran_pokok)
    else:
        bulan_terpenuhi = 0

    cicilan_terbayar = min(bulan_terpenuhi, tenor)

    # ── Deteksi tunggakan ────────────────────────────────────────────────
    bulan_sudah_jatuh_tempo = sum(
        1 for i in range(tenor)
        if akhir_bulan(tanggal_cicilan_ke(i)) < today
    )
    bulan_seharusnya   = min(bulan_sudah_jatuh_tempo, tenor)
    bulan_nunggak      = max(bulan_seharusnya - cicilan_terbayar, 0)
    sisa_cicilan_total = max(tenor - cicilan_terbayar, 0)
    ada_tunggakan      = bulan_nunggak > 0

    # ── Daftar bulan yang nunggak ─────────────────────────────────────────
    def format_bulan_indo(tgl):
        return (
            tgl.strftime("%B %Y")
               .replace("January","Januari").replace("February","Februari")
               .replace("March","Maret").replace("April","April")
               .replace("May","Mei").replace("June","Juni")
               .replace("July","Juli").replace("August","Agustus")
               .replace("September","September").replace("October","Oktober")
               .replace("November","November").replace("December","Desember")
        )

    daftar_bulan_nunggak = []
    if ada_tunggakan:
        for i in range(cicilan_terbayar, bulan_seharusnya):
            daftar_bulan_nunggak.append(format_bulan_indo(tanggal_cicilan_ke(i)))

    # ── Helper jasa ───────────────────────────────────────────────────────
    def hitung_jasa(sisa):
        if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
            return sisa * (jasa_persen / 100)
        return jumlah_pinjaman * (jasa_persen / 100)

    # ── Pilihan bulan kewajiban ───────────────────────────────────────────
    # Kasus: bayar normal bulan Mei (cicilan_terbayar naik ke 1) → bulan Mei
    # hilang dari range(1, tenor). Padahal sisa masih ada → harus include.
    # Solusi: prepend bulan cicilan_terbayar-1 jika masih ada sisa & ada cicilannya.
    pilihan_bulan = []

    if cicilan_terbayar > 0 and sisa_pinjaman > 0:
        idx_prev = cicilan_terbayar - 1
        tgl_prev = tanggal_cicilan_ke(idx_prev)
        if (tgl_prev.year, tgl_prev.month) in bulan_sudah_cicilan:
            pilihan_bulan.append({
                "value"            : idx_prev,
                "label"            : format_bulan_indo(tgl_prev),
                "sudah_ada_cicilan": True,
            })

    for idx in range(cicilan_terbayar, tenor):
        tgl = tanggal_cicilan_ke(idx)
        sudah_ada_cicilan = (tgl.year, tgl.month) in bulan_sudah_cicilan
        pilihan_bulan.append({
            "value"            : idx,
            "label"            : format_bulan_indo(tgl),
            "sudah_ada_cicilan": sudah_ada_cicilan,
        })

    bulan_kewajiban_default = pilihan_bulan[0]["value"] if pilihan_bulan else cicilan_terbayar

    # ── Jasa default (untuk bulan default) ───────────────────────────────
    tgl_default         = tanggal_cicilan_ke(bulan_kewajiban_default)
    sudah_bayar_default = (tgl_default.year, tgl_default.month) in bulan_sudah_cicilan

    jasa_bulan_ini      = Decimal("0") if sudah_bayar_default else hitung_jasa(sisa_pinjaman)
    jasa_penuh          = hitung_jasa(sisa_pinjaman)
    acuan_per_bulan     = angsuran_pokok + jasa_penuh
    total_bayar_default = (angsuran_pokok + jasa_bulan_ini) if sisa_pinjaman > 0 else Decimal("0")

    # ── POST ─────────────────────────────────────────────────────────────
    if request.method == "POST":

        tipe_bayar      = request.POST.get("tipe_bayar")
        nominal_raw     = request.POST.get("nominal", "0")
        jumlah_bln_jasa = int(request.POST.get("jumlah_bulan_jasa", 1) or 1)
        bulan_idx_str   = request.POST.get("bulan_kewajiban")

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

        # ── Validasi batas bawah bulan ────────────────────────────────────
        # Bulan cicilan_terbayar-1 boleh dipilih hanya jika sisa > 0
        # dan bulan itu memang sudah ada cicilannya (kasus pelunasan bulan yg sama)
        batas_bawah = cicilan_terbayar
        if cicilan_terbayar > 0 and sisa_pinjaman > 0:
            idx_prev = cicilan_terbayar - 1
            tgl_prev = tanggal_cicilan_ke(idx_prev)
            if (tgl_prev.year, tgl_prev.month) in bulan_sudah_cicilan:
                batas_bawah = idx_prev

        if bulan_kewajiban_idx < batas_bawah:
            messages.error(request, "Bulan kewajiban tidak valid (sudah terbayar penuh).")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        # ── Validasi tunggakan ────────────────────────────────────────────
        # Jika ada tunggakan, bulan yang boleh dipilih hanya:
        # - cicilan_terbayar (bulan tunggakan pertama), ATAU
        # - cicilan_terbayar-1 jika itu adalah kasus pelunasan di bulan yang sama
        # Bulan lain (lebih besar dari cicilan_terbayar) tidak boleh dilompat.
        if ada_tunggakan:
            bulan_boleh = {cicilan_terbayar}
            if batas_bawah < cicilan_terbayar:
                bulan_boleh.add(batas_bawah)
            if bulan_kewajiban_idx not in bulan_boleh:
                messages.error(request, "Terdapat tunggakan. Harus lunasi tunggakan terlebih dahulu.")
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

        tanggal_input_str = request.POST.get("tanggal")
        if not tanggal_input_str:
            messages.error(request, "Tanggal wajib diisi.")
            return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)
        tanggal_input = datetime.strptime(tanggal_input_str, "%Y-%m-%d").date()

        tgl_kewajiban = tanggal_cicilan_ke(bulan_kewajiban_idx)

        sudah_bayar_cicilan_bulan_dipilih = (
            tgl_kewajiban.year, tgl_kewajiban.month
        ) in bulan_sudah_cicilan

        # ── Tipe cicilan ──────────────────────────────────────────────────
        if tipe_bayar == "cicilan":

            pokok_raw = request.POST.get("nominal_pokok", "")
            try:
                pokok_dibayar = Decimal(
                    pokok_raw.replace("Rp", "").replace(".", "").replace(",", "").strip()
                )
            except Exception:
                pokok_dibayar = angsuran_pokok

            pokok_minimal = min(angsuran_pokok, sisa_pinjaman)
            if pokok_dibayar < pokok_minimal:
                messages.error(request, f"Pokok minimal Rp {pokok_minimal:,.0f}.")
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            if pokok_dibayar > sisa_pinjaman:
                pokok_dibayar = sisa_pinjaman

            jasa_cicilan = Decimal("0") if sudah_bayar_cicilan_bulan_dipilih else hitung_jasa(sisa_pinjaman)
            total_wajib  = pokok_dibayar + jasa_cicilan

            if nominal < total_wajib:
                messages.error(
                    request,
                    f"Nominal kurang. Minimal Rp {total_wajib:,.0f} "
                    f"(pokok Rp {pokok_dibayar:,.0f} + jasa Rp {jasa_cicilan:,.0f})."
                )
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            # tgl_kewajiban sudah dihitung sebelumnya: tanggal_cicilan_ke(bulan_kewajiban_idx)
            # ambil tanggal pertama bulan itu sebagai bulan_kewajiban
            bulan_kewajiban_date = tgl_kewajiban.replace(day=1)

            Angsuran.objects.create(
                id_pinjaman    = pinjaman,
                id_admin       = admin_login,
                tanggal_bayar  = tanggal_input,
                jumlah_bayar   = pokok_dibayar + jasa_cicilan,
                jumlah_pokok   = pokok_dibayar,
                tipe_bayar     = "cicilan",
                bulan_kewajiban= bulan_kewajiban_date,   # ← field baru
            )

            pinjaman.sisa_pinjaman = max(sisa_pinjaman - pokok_dibayar, Decimal("0"))

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

        # ── Tipe jasa saja ────────────────────────────────────────────────
        elif tipe_bayar == "jasa":

            if jumlah_bln_jasa < 1:
                jumlah_bln_jasa = 1

            jasa_per_bulan = hitung_jasa(sisa_pinjaman)
            total_jasa     = jasa_per_bulan * jumlah_bln_jasa

            if nominal < total_jasa:
                messages.error(
                    request,
                    f"Nominal kurang. Total jasa {jumlah_bln_jasa} bulan = Rp {total_jasa:,.0f}."
                )
                return redirect("pinjaman:bayar_pinjaman", id_pinjaman=id_pinjaman)

            for i in range(jumlah_bln_jasa):
                Angsuran.objects.create(
                    id_pinjaman    = pinjaman,
                    id_admin       = admin_login,
                    tanggal_bayar  = tanggal_input,
                    jumlah_bayar   = jasa_per_bulan,
                    jumlah_pokok   = Decimal("0"),
                    tipe_bayar     = "jasa",
                    # jasa tidak punya bulan kewajiban spesifik → biarkan None
                )

        # ── Update status ─────────────────────────────────────────────────
        if pinjaman.sisa_pinjaman <= 0:
            pinjaman.status = "Lunas"
        pinjaman.save()

        messages.success(request, "Pembayaran berhasil disimpan.")
        return redirect("pinjaman:pinjaman_list")

    # ── GET ───────────────────────────────────────────────────────────────
    return render(request, "form/bayar_pinjaman.html", {
        "pinjaman"                : pinjaman,
        "angsuran_pokok"          : angsuran_pokok,
        "jasa_bulan_ini"          : jasa_bulan_ini,
        "acuan_per_bulan"         : acuan_per_bulan,
        "sisa_pokok_nominal"      : sisa_pinjaman,
        "sisa_cicilan_total"      : sisa_cicilan_total,
        "bulan_nunggak"           : bulan_nunggak,
        "ada_tunggakan"           : ada_tunggakan,
        "daftar_bulan_nunggak"    : daftar_bulan_nunggak,
        "pilihan_bulan"           : pilihan_bulan,
        "bulan_kewajiban_default" : bulan_kewajiban_default,
        "total_bayar_default"     : total_bayar_default,
        "jasa_persen"             : jasa_persen,
        "jasa_penuh"              : jasa_penuh,
        "jasa_sudah_dibayar"      : sudah_bayar_default,
        "jasa_bulan_ini_penuh"    : jasa_penuh,
    })


# fungsi: menampilkan detail satu transaksi pembayaran
def detail_pembayaran(request, pembayaran_id):

    pembayaran = get_object_or_404(Angsuran, id_pembayaran=pembayaran_id)
    pinjaman   = pembayaran.id_pinjaman

    semua_angsuran = Angsuran.objects.filter(
        id_pinjaman=pinjaman
    ).order_by('tanggal_bayar', 'id_pembayaran')

    # ── Rekonstruksi sisa pokok kumulatif ────────────────────────────────
    sisa_running = Decimal(pinjaman.jumlah_pinjaman or 0)
    sisa_sebelum = sisa_running
    sisa_setelah = sisa_running

    for angsuran in semua_angsuran:
        if angsuran.id_pembayaran == pembayaran.id_pembayaran:
            sisa_sebelum = sisa_running
            if angsuran.tipe_bayar == "cicilan":
                pokok         = angsuran.jumlah_pokok or Decimal(pinjaman.angsuran_per_bulan or 0)
                sisa_running -= pokok
            sisa_setelah = sisa_running
            break
        else:
            if angsuran.tipe_bayar == "cicilan":
                pokok         = angsuran.jumlah_pokok or Decimal(pinjaman.angsuran_per_bulan or 0)
                sisa_running -= pokok

    sisa_sebelum = max(sisa_sebelum, Decimal("0"))
    sisa_setelah = max(sisa_setelah, Decimal("0"))

    # ── Hitung jasa untuk pembayaran ini ─────────────────────────────────
    # FIX: cek apakah sebelum pembayaran ini di bulan yang sama sudah ada
    # pembayaran cicilan/jasa lain → kalau sudah, jasa pembayaran ini = 0
    jasa_persen = pinjaman.jasa_persen or Decimal("0")

    def hitung_jasa_dari_sisa(sisa):
        if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
            return sisa * (jasa_persen / 100)
        return Decimal(pinjaman.jumlah_pinjaman or 0) * (jasa_persen / 100)

    if pembayaran.tipe_bayar == "cicilan":
        # Cek apakah ada pembayaran cicilan/jasa lain di bulan & tahun yang sama
        # yang terjadi SEBELUM pembayaran ini (berdasarkan id_pembayaran lebih kecil)
        sudah_ada_bayar_bulan_itu = Angsuran.objects.filter(
            id_pinjaman   = pinjaman,
            tipe_bayar__in= ['cicilan', 'jasa'],
            tanggal_bayar__year  = pembayaran.tanggal_bayar.year,
            tanggal_bayar__month = pembayaran.tanggal_bayar.month,
        ).exclude(
            id_pembayaran = pembayaran.id_pembayaran
        ).filter(
            id_pembayaran__lt = pembayaran.id_pembayaran
        ).exists()

        jasa_rupiah = Decimal("0") if sudah_ada_bayar_bulan_itu else hitung_jasa_dari_sisa(sisa_sebelum)
    else:
        # Tipe jasa saja: jasa_rupiah = jumlah_bayar itu sendiri
        jasa_rupiah = pembayaran.jumlah_bayar

    # ── Jumlah pembayaran untuk ditampilkan ──────────────────────────────
    if pembayaran.tipe_bayar == "jasa":
        jumlah_pembayaran = pembayaran.jumlah_bayar
    else:
        jumlah_pembayaran = pembayaran.jumlah_bayar  # sudah = pokok + jasa saat disimpan

    return render(request, 'detail/detail_pembayaran.html', {
        'pembayaran'       : pembayaran,
        'sisa_sebelum'     : sisa_sebelum,
        'sisa_setelah'     : sisa_setelah,
        'jasa_rupiah'      : jasa_rupiah,
        'jumlah_pembayaran': jumlah_pembayaran,
    })