from django.db import models
from anggota.models import Anggota
from admin_koperasi.models import User
from django.conf import settings



# =========================
# KATEGORI JASA
# =========================
class KategoriJasa(models.Model):
    id_kategori_jasa = models.BigAutoField(primary_key=True)
    kategori_jasa = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'Kategori_Jasa'

    def __str__(self):
        return self.kategori_jasa


# =========================
# JENIS PINJAMAN
# =========================
class JenisPinjaman(models.Model):
    JENIS_PINJAMAN_CHOICES = [
        ('Reguler', 'Reguler'),
        ('Khusus', 'Khusus'),
        ('Barang', 'Barang'),
    ]

    id_jenis_pinjaman = models.BigAutoField(primary_key=True)
    nama_jenis = models.CharField(max_length=50, choices=JENIS_PINJAMAN_CHOICES)

    class Meta:
        db_table = 'Jenis_Pinjaman'

    def __str__(self):
        return self.nama_jenis


# =========================
# PINJAMAN (MIRIP CONTOH)
# =========================
class Pinjaman(models.Model):
    id_pinjaman = models.BigAutoField(primary_key=True)

    # ⚠️ NAMA FIELD DISAMAAN
    nomor_anggota = models.ForeignKey(
        Anggota,
        on_delete=models.CASCADE,
        db_column='anggota_id'
    )

    id_jenis_pinjaman = models.ForeignKey(
        JenisPinjaman,
        on_delete=models.CASCADE,
        db_column='jenis_pinjaman_id'
    )

    id_kategori_jasa = models.ForeignKey(
        KategoriJasa,
        on_delete=models.CASCADE,
        default=1,
        db_column='kategori_jasa_id'
    )

    # ⚠️ Admin → User (custom admin kamu)
    id_admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='admin_id'
    )

    jumlah_pinjaman = models.DecimalField(max_digits=18, decimal_places=2)
    angsuran_per_bulan = models.DecimalField(max_digits=18, decimal_places=2)

    jasa_persen = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    jasa_rupiah = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True
    )

    tanggal_meminjam = models.DateField()

    jatuh_tempo = models.PositiveIntegerField(
        help_text="Lama pinjaman dalam bulan"
    )

    sisa_pinjaman = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    status = models.CharField(max_length=20)

    class Meta:
        db_table = 'Pinjaman'

    def __str__(self):
        return f"Pinjaman {self.id_pinjaman} - {self.nomor_anggota.nama}"

    # =========================
    # LOGIC (SAMA DENGAN CONTOH)
    # =========================
    def hitung_jasa(self):
        if self.jasa_persen and self.jumlah_pinjaman:
            return self.jumlah_pinjaman * (self.jasa_persen / 100)
        return 0

    def sisa(self):
        return self.sisa_pinjaman


# =========================
# ANGSURAN (MIRIP CONTOH)
# =========================
class Angsuran(models.Model):
    id_pembayaran = models.BigAutoField(primary_key=True)

    id_pinjaman = models.ForeignKey(
        Pinjaman,
        on_delete=models.CASCADE,
        db_column='id_pinjaman'
    )

    id_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_admin',
        related_name='angsuran_admin'
    )


    jumlah_bayar = models.DecimalField(max_digits=18, decimal_places=2)
    tanggal_bayar = models.DateField()

    TIPE_BAYAR_CHOICES = (
        ('cicilan', 'Cicilan + Jasa'),
        ('jasa', 'Jasa Saja'),
    )

    tipe_bayar = models.CharField(
        max_length=10,
        choices=TIPE_BAYAR_CHOICES,
        default='cicilan'
    )

    class Meta:
        db_table = 'Angsuran'

    def __str__(self):
        return f"Angsuran {self.id_pembayaran} - Pinjaman {self.id_pinjaman.id_pinjaman}"
