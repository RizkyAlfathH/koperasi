from django.db import models
from anggota.models import Anggota
from admin_koperasi.models import User
import datetime

# ======================
# Model Jenis Simpanan
# ======================
class JenisSimpanan(models.Model):
    POKOK = "POKOK"
    WAJIB = "WAJIB"
    SUKARELA = "SUKARELA"

    JENIS_CHOICES = [
        (POKOK, "Simpanan Pokok"),
        (WAJIB, "Simpanan Wajib"),
        (SUKARELA, "Simpanan Sukarela"),
    ]

    nama_jenis = models.CharField(
        max_length=20,
        choices=JENIS_CHOICES,
        unique=True
    )

    class Meta:
        db_table = "jenis_simpanan"

    def __str__(self):
        return self.get_nama_jenis_display()


# ======================
# Model Simpanan
# ======================
class Simpanan(models.Model):
    anggota = models.ForeignKey(
        Anggota,
        on_delete=models.CASCADE,
        related_name="simpanan"
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # supaya tidak bisa dihapus jika masih dipakai di simpanan
        null=True,                 # wajib diisi
        blank=False
    )
    jenis_simpanan = models.ForeignKey(
        JenisSimpanan,
        on_delete=models.SET_NULL,
        null=True
    )
    tanggal = models.DateField(default=datetime.date.today)
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)
    dana_sosial = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        db_table = "simpanan"
        ordering = ["-tanggal"]

    def __str__(self):
        return f"{self.anggota} - {self.jenis_simpanan}"

    def save(self, *args, **kwargs):
        # Simpan transaksi
        super().save(*args, **kwargs)
        HistoryTabungan.objects.create(
            anggota=self.anggota,
            jenis_simpanan=self.jenis_simpanan,
            tanggal=self.tanggal,
            jenis_transaksi="SETOR",
            jumlah=self.jumlah
        )


# ======================
# Model Penarikan
# ======================
class Penarikan(models.Model):
    anggota = models.ForeignKey(
        Anggota,
        on_delete=models.CASCADE,
        related_name="penarikan"
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # supaya tidak bisa dihapus jika masih dipakai di simpanan
        null=True,                 # wajib diisi
        blank=False
    )
    jenis_simpanan = models.ForeignKey(
        JenisSimpanan,
        on_delete=models.SET_NULL,
        null=True
    )
    tanggal = models.DateField(default=datetime.date.today)
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        db_table = "penarikan"
        ordering = ["-tanggal"]

    def __str__(self):
        return f"{self.anggota.nama} - tarik {self.jumlah}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        HistoryTabungan.objects.create(
            anggota=self.anggota,
            jenis_simpanan=self.jenis_simpanan,
            tanggal=self.tanggal,
            jenis_transaksi="TARIK",
            jumlah=self.jumlah
        )


# ======================
# Model History Tabungan
# ======================
class HistoryTabungan(models.Model):
    SETOR = "SETOR"
    TARIK = "TARIK"
    KOREKSI = "KOREKSI"

    JENIS_TRANSAKSI = [
        (SETOR, "Setor"),
        (TARIK, "Tarik"),
        (KOREKSI, "Koreksi")
    ]

    anggota = models.ForeignKey(Anggota, on_delete=models.CASCADE)
    jenis_simpanan = models.ForeignKey(JenisSimpanan, on_delete=models.SET_NULL, null=True, blank=True)
    tanggal = models.DateField(default=datetime.date.today)
    jenis_transaksi = models.CharField(max_length=10, choices=JENIS_TRANSAKSI)
    jumlah = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        db_table = "history_tabungan"
        ordering = ["-tanggal"]

    def __str__(self):
        return f"{self.anggota.nama} - {self.jenis_transaksi} {self.jumlah}"
