from django.db import models
from anggota.models import Anggota
from admin_koperasi.models import User
from django.conf import settings
from decimal import Decimal


# class: model untuk menyimpan kategori jasa (misal turunan / tetap)
class KategoriJasa(models.Model):
    # field: primary key otomatis
    id_kategori_jasa = models.BigAutoField(primary_key=True)

    # field: nama kategori jasa, harus unik
    kategori_jasa = models.CharField(max_length=50, unique=True)

    # class meta: konfigurasi tambahan untuk model
    class Meta:
        db_table = 'Kategori_Jasa'  # nama tabel di database

    # method: representasi string saat object dipanggil
    def __str__(self):
        return self.kategori_jasa

# class: model untuk jenis pinjaman (reguler, khusus, barang)
class JenisPinjaman(models.Model):
    # konstanta: pilihan jenis pinjaman
    JENIS_PINJAMAN_CHOICES = [
        ('Reguler', 'Reguler'),
        ('Khusus', 'Khusus'),
        ('Barang', 'Barang'),
    ]

    # field: primary key
    id_jenis_pinjaman = models.BigAutoField(primary_key=True)

    # field: nama jenis dengan pilihan tertentu
    nama_jenis = models.CharField(max_length=50, choices=JENIS_PINJAMAN_CHOICES)

    # class meta: nama tabel
    class Meta:
        db_table = 'Jenis_Pinjaman'

    # method: representasi string object
    def __str__(self):
        return self.nama_jenis


# class: model utama pinjaman
class Pinjaman(models.Model):
    # field: primary key
    id_pinjaman = models.BigAutoField(primary_key=True)

    # relasi: ke model anggota (foreign key)
    nomor_anggota = models.ForeignKey(
        Anggota,
        on_delete=models.CASCADE,
        db_column='anggota_id'
    )

    # relasi: ke jenis pinjaman
    id_jenis_pinjaman = models.ForeignKey(
        JenisPinjaman,
        on_delete=models.CASCADE,
        db_column='jenis_pinjaman_id'
    )

    # relasi: ke kategori jasa
    id_kategori_jasa = models.ForeignKey(
        KategoriJasa,
        on_delete=models.CASCADE,
        default=1,
        db_column='kategori_jasa_id'
    )

    # relasi: ke user (admin yang input)
    id_admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='admin_id'
    )

    # field: jumlah pinjaman awal
    jumlah_pinjaman = models.DecimalField(max_digits=18, decimal_places=2)

    # field: cicilan pokok per bulan
    angsuran_per_bulan = models.DecimalField(max_digits=18, decimal_places=2)

    # field: persen jasa (opsional)
    jasa_persen = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # field: nilai jasa dalam rupiah (opsional)
    jasa_rupiah = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True
    )

    # field: tanggal mulai pinjaman
    tanggal_meminjam = models.DateField()

    # field: lama pinjaman (bulan)
    jatuh_tempo = models.PositiveIntegerField(
        help_text="Lama pinjaman dalam bulan"
    )

    # field: sisa pinjaman yang belum dibayar
    sisa_pinjaman = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    # field: status pinjaman (aktif, lunas, digabung)
    status = models.CharField(max_length=20)

    # class meta: nama tabel
    class Meta:
        db_table = 'Pinjaman'

    # method: representasi string object
    def __str__(self):
        return f"Pinjaman {self.id_pinjaman} - {self.nomor_anggota.nama}"
    
    # method: menghitung sisa pinjaman real berdasarkan jumlah cicilan
    def hitung_sisa_pinjaman_real(self):
        # query: hitung jumlah cicilan
        cicilan = Angsuran.objects.filter(
            id_pinjaman=self,
            tipe_bayar="cicilan"
        ).count()

        # proses: hitung sisa pinjaman
        sisa = self.jumlah_pinjaman - (Decimal(cicilan) * self.angsuran_per_bulan)

        # return: pastikan tidak negatif
        return max(sisa, Decimal("0"))

    # method: menghitung jasa berdasarkan persen
    def hitung_jasa(self):
        if self.jasa_persen and self.jumlah_pinjaman:
            return self.jumlah_pinjaman * (self.jasa_persen / 100)
        return 0

    # method: getter sederhana untuk sisa pinjaman
    def sisa(self):
        return self.sisa_pinjaman


# class: model untuk menyimpan data pembayaran / angsuran
class Angsuran(models.Model):
    # field: primary key
    id_pembayaran = models.BigAutoField(primary_key=True)

    # relasi: ke pinjaman
    id_pinjaman = models.ForeignKey(
        Pinjaman,
        on_delete=models.CASCADE,
        db_column='id_pinjaman'
    )

    # relasi: ke admin (user)
    id_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_admin',
        related_name='angsuran_admin'
    )

    jumlah_pokok = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )

    # field: jumlah pembayaran
    jumlah_bayar = models.DecimalField(max_digits=18, decimal_places=2)

    # field: tanggal pembayaran
    tanggal_bayar = models.DateField()

    # konstanta: pilihan tipe pembayaran
    TIPE_BAYAR_CHOICES = (
        ('cicilan', 'Cicilan + Jasa'),
        ('jasa', 'Jasa Saja'),
    )

    # field: tipe pembayaran
    tipe_bayar = models.CharField(
        max_length=10,
        choices=TIPE_BAYAR_CHOICES,
        default='cicilan'
    )

    # class meta: nama tabel
    class Meta:
        db_table = 'Angsuran'

    # method: representasi string object
    def __str__(self):
        return f"Angsuran {self.id_pembayaran} - Pinjaman {self.id_pinjaman.id_pinjaman}"
