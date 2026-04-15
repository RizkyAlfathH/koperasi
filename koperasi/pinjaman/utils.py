# koperasi/pinjaman/utils.py

from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Sum


def cek_auto_sukarela_ke_pinjaman(pinjaman, admin_login):
    from pinjaman.models import Angsuran
    from simpanan.models import Simpanan, JenisSimpanan

    today = date.today()

    if pinjaman.status.lower() == "lunas":
        return

    angsuran_pokok  = Decimal(pinjaman.angsuran_per_bulan or 0)
    jasa_persen     = Decimal(pinjaman.jasa_persen or 0)
    jumlah_pinjaman = Decimal(pinjaman.jumlah_pinjaman or 0)
    tanggal_mulai   = pinjaman.tanggal_meminjam

    cicilan_terbayar = Angsuran.objects.filter(
        id_pinjaman=pinjaman,
        tipe_bayar="cicilan"
    ).count()

    bulan_total_berjalan = (
        (today.year - tanggal_mulai.year) * 12
        + (today.month - tanggal_mulai.month)
    )

    bulan_belum_bayar = bulan_total_berjalan - cicilan_terbayar

    if bulan_belum_bayar <= 0:
        return

    jenis_sukarela, _ = JenisSimpanan.objects.get_or_create(nama_jenis="SUKARELA")

    for i in range(bulan_belum_bayar):

        cicilan_sekarang = Angsuran.objects.filter(
            id_pinjaman=pinjaman,
            tipe_bayar="cicilan"
        ).count()

        sisa_pinjaman = jumlah_pinjaman - (cicilan_sekarang * angsuran_pokok)
        sisa_pinjaman = max(sisa_pinjaman, Decimal("0"))

        if sisa_pinjaman <= 0:
            pinjaman.status = "Lunas"
            pinjaman.sisa_pinjaman = 0
            pinjaman.save()
            return

        if pinjaman.id_kategori_jasa.kategori_jasa.lower() == "turunan":
            jasa_rupiah = sisa_pinjaman * (jasa_persen / Decimal("100"))
        else:
            jasa_rupiah = jumlah_pinjaman * (jasa_persen / Decimal("100"))

        total_bulan_ini = angsuran_pokok + jasa_rupiah

        saldo_sukarela = Simpanan.objects.filter(
            anggota=pinjaman.nomor_anggota,
            jenis_simpanan__nama_jenis__iexact="SUKARELA",
            sumber_pinjaman=pinjaman
        ).aggregate(total=Sum("jumlah"))["total"] or Decimal("0")

        if saldo_sukarela < total_bulan_ini:
            break

        # FIX: bulan_ke = cicilan_sekarang (bukan +1)
        # cicilan_sekarang=1 (sudah bayar April) → +1 bulan = Mei ✓
        bulan_ke = cicilan_sekarang + 1  # +1 karena cicilan_sekarang = jumlah yg sudah terbayar
        tanggal_bayar = (tanggal_mulai + relativedelta(months=bulan_ke)).replace(day=1)

        Simpanan.objects.create(
            anggota=pinjaman.nomor_anggota,
            admin=admin_login,
            jenis_simpanan=jenis_sukarela,
            tanggal=tanggal_bayar,
            jumlah=-total_bulan_ini,
            sumber_pinjaman=pinjaman
        )

        Angsuran.objects.create(
            id_pinjaman=pinjaman,
            id_admin=admin_login,
            tanggal_bayar=tanggal_bayar,
            jumlah_bayar=total_bulan_ini,
            tipe_bayar="cicilan"
        )

        pinjaman.sisa_pinjaman = sisa_pinjaman - angsuran_pokok
        if pinjaman.sisa_pinjaman <= 0:
            pinjaman.sisa_pinjaman = 0
            pinjaman.status = "Lunas"
            pinjaman.save()
            return

        pinjaman.save(update_fields=["sisa_pinjaman"])