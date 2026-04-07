from django.db import models
from anggota.models import Anggota
from pinjaman.models import Pinjaman
from admin_koperasi.models import User
import datetime

# class: model untuk jenis simpanan (master data)
class JenisSimpanan(models.Model):

    # konstanta (variabel class): nilai jenis simpanan
    Pokok = "Pokok"
    Wajib = "Wajib"
    Sukarela = "Sukarela"

    # konstanta (list pilihan): digunakan pada field choices
    JENIS_CHOICES = [
        (Pokok, "Simpanan Pokok"),
        (Wajib, "Simpanan Wajib"),
        (Sukarela, "Simpanan Sukarela"),
    ]

    # field (model): nama jenis simpanan
    nama_jenis = models.CharField(
        max_length=20,
        choices=JENIS_CHOICES,
        unique=True
    )

    # class meta: konfigurasi tabel database
    class Meta:
        db_table = "jenis_simpanan"

    # method: representasi string object
    def __str__(self):
        return self.get_nama_jenis_display()


# class: model untuk transaksi simpanan (setoran)
class Simpanan(models.Model):

    # field (relasi): relasi ke model anggota
    anggota = models.ForeignKey(
        Anggota,
        on_delete=models.CASCADE,
        related_name="simpanan"
    )

    # field (relasi): admin yang melakukan input
    admin = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # tidak bisa dihapus jika masih digunakan
        null=True,
        blank=False
    )

    # field (relasi): jenis simpanan
    jenis_simpanan = models.ForeignKey(
        JenisSimpanan,
        on_delete=models.SET_NULL,
        null=True
    )

    # field (model): tanggal transaksi
    tanggal = models.DateField(default=datetime.date.today)

    # field (model): jumlah simpanan
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)

    # field (model): dana sosial
    dana_sosial = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # field (relasi): sumber dari pinjaman (opsional)
    sumber_pinjaman = models.ForeignKey(
        Pinjaman,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # class meta: konfigurasi tabel dan urutan data
    class Meta:
        db_table = "simpanan"
        ordering = ["-tanggal"]

    # method: representasi string object
    def __str__(self):
        return f"{self.anggota} - {self.jenis_simpanan}"

    # method: override save (dipanggil saat data disimpan)
    def save(self, *args, **kwargs):
        # simpan data utama ke database
        super().save(*args, **kwargs)

        # objek: membuat histori otomatis setiap simpanan
        HistoryTabungan.objects.create(
            anggota=self.anggota,
            jenis_simpanan=self.jenis_simpanan,
            tanggal=self.tanggal,
            jenis_transaksi="SETOR",
            jumlah=self.jumlah,
            sumber_pinjaman=self.sumber_pinjaman
        )


# class: model untuk transaksi penarikan
class Penarikan(models.Model):

    # field (relasi): anggota yang melakukan penarikan
    anggota = models.ForeignKey(
        Anggota,
        on_delete=models.CASCADE,
        related_name="penarikan"
    )

    # field (relasi): admin yang memproses
    admin = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=False
    )

    # field (relasi): jenis simpanan yang ditarik
    jenis_simpanan = models.ForeignKey(
        JenisSimpanan,
        on_delete=models.SET_NULL,
        null=True
    )

    # field (model): tanggal penarikan
    tanggal = models.DateField(default=datetime.date.today)

    # field (model): jumlah penarikan
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)

    # class meta: konfigurasi tabel dan urutan data
    class Meta:
        db_table = "penarikan"
        ordering = ["-tanggal"]

    # method: representasi string object
    def __str__(self):
        return f"{self.anggota.nama} - tarik {self.jumlah}"

    # method: override save untuk membuat histori otomatis
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # objek: simpan ke history sebagai transaksi tarik
        HistoryTabungan.objects.create(
            anggota=self.anggota,
            jenis_simpanan=self.jenis_simpanan,
            tanggal=self.tanggal,
            jenis_transaksi="TARIK",
            jumlah=self.jumlah
        )


# class: model untuk mencatat histori semua transaksi tabungan
class HistoryTabungan(models.Model):

    # konstanta (variabel class): jenis transaksi
    SETOR = "SETOR"
    TARIK = "TARIK"
    KOREKSI = "KOREKSI"

    # konstanta (choices): pilihan jenis transaksi
    JENIS_TRANSAKSI = [
        (SETOR, "Setor"),
        (TARIK, "Tarik"),
        (KOREKSI, "Koreksi")
    ]

    # field (relasi): anggota terkait
    anggota = models.ForeignKey(Anggota, on_delete=models.CASCADE)

    # field (relasi): jenis simpanan
    jenis_simpanan = models.ForeignKey(
        JenisSimpanan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # field (relasi): sumber pinjaman (opsional)
    sumber_pinjaman = models.ForeignKey(
        Pinjaman,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # field (model): tanggal transaksi
    tanggal = models.DateField(default=datetime.date.today)

    # field (model): jenis transaksi (setor, tarik, koreksi)
    jenis_transaksi = models.CharField(
        max_length=10,
        choices=JENIS_TRANSAKSI
    )

    # field (model): jumlah transaksi
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)

    # class meta: konfigurasi tabel dan sorting
    class Meta:
        db_table = "history_tabungan"
        ordering = ["-tanggal"]

    # method: representasi string object
    def __str__(self):
        return f"{self.anggota.nama} - {self.jenis_transaksi} {self.jumlah}"