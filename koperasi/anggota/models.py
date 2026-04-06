from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime
from django.db.models import Sum
from django.utils import timezone

# class model Anggota (turunan dari models.Model)
class Anggota(models.Model):

    # atribut class (konstanta pilihan jenis kelamin)
    JK_CHOICES = [
        ('Laki-laki', 'Laki-laki'),
        ('Perempuan', 'Perempuan'),
    ]

    # atribut class (konstanta pilihan status)
    STATUS_CHOICES = [
        ('aktif', 'Aktif'),
        ('nonaktif', 'Nonaktif'),
    ]

    # field database (objek dari models.CharField)
    nomor_anggota = models.CharField(
        max_length=20,
        unique=True,
        primary_key=True  # primary key tabel
    )

    # field nama
    nama = models.CharField(max_length=100)

    # field umur (boleh null)
    umur = models.IntegerField(null=True)

    # field nip (tidak harus unik)
    nip = models.CharField(max_length=30, unique=False, null=True)

    # field alamat
    alamat = models.CharField(max_length=255, null=True)

    # field nomor telepon
    no_telp = models.CharField(max_length=40, null=True)

    # field email
    email = models.CharField(max_length=255, null=True)

    # field jenis kelamin dengan pilihan (choices)
    jenis_kelamin = models.CharField(
        max_length=10,
        choices=JK_CHOICES
    )

    # field pekerjaan
    pekerjaan = models.CharField(max_length=255, null=True)

    # field tanggal daftar (default tanggal sekarang)
    tanggal_daftar = models.DateField(default=timezone.now)

    # field status anggota
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='aktif'
    )

    # field alasan nonaktif (opsional)
    alasan_nonaktif = models.CharField(max_length=255, blank=True, null=True)

    # field tanggal nonaktif
    tanggal_nonaktif = models.DateField(blank=True, null=True)

    # field untuk menyimpan password terenkripsi
    password_hash = models.CharField(max_length=255)

    # class Meta untuk konfigurasi model
    class Meta:
        db_table = 'Anggota'  # nama tabel di database

    # method untuk representasi string objek
    def __str__(self):
        return f"{self.nomor_anggota} - {self.nama}"

    # method untuk set password (hashing)
    def set_password(self, raw_password: str):
        # make_password = fungsi Django untuk enkripsi password
        self.password_hash = make_password(raw_password)

    # method untuk cek password
    def check_password(self, raw_password: str) -> bool:
        # check_password = fungsi untuk membandingkan hash
        return check_password(raw_password, self.password_hash)

    # method untuk menghitung total simpanan
    def get_total_simpanan(self):
        # self.simpanan = relasi (reverse relation dari model Simpanan)
        return self.simpanan.aggregate(
            total=Sum('jumlah')  # aggregate = method ORM
        )['total'] or 0

    # method untuk menghitung total penarikan
    def get_total_penarikan(self):
        # self.penarikan = relasi ke model Penarikan
        return self.penarikan.aggregate(
            total=Sum('jumlah')
        )['total'] or 0

    # method untuk menghitung saldo akhir
    def get_saldo(self):
        # memanggil method lain dalam class
        return self.get_total_simpanan() - self.get_total_penarikan()