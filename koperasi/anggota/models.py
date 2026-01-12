from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime
from django.db.models import Sum

class Anggota(models.Model):
    JK_CHOICES = [
        ('Laki-laki', 'Laki-laki'),
        ('Perempuan', 'Perempuan'),
    ]
    STATUS_CHOICES = [
        ('aktif', 'Aktif'),
        ('nonaktif', 'Nonaktif'),
    ]

    nomor_anggota = models.CharField(max_length=20, unique=True, primary_key=True)
    nama = models.CharField(max_length=100)
    umur = models.IntegerField(blank=True, null=True)
    nip = models.CharField(max_length=30, unique=False, blank=True, null=True)
    alamat = models.CharField(max_length=255, blank=True, null=True)
    no_telp = models.CharField(max_length=40, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    jenis_kelamin = models.CharField(max_length=10, choices=JK_CHOICES)
    pekerjaan = models.CharField(max_length=255, blank=True, null=True)  
    tanggal_daftar = models.DateField(default=datetime.now)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='aktif')
    alasan_nonaktif = models.CharField(max_length=255, blank=True, null=True)
    tanggal_nonaktif = models.DateField(blank=True, null=True)
    password_hash = models.CharField(max_length=255)

    class Meta:
        db_table = 'Anggota'

    def __str__(self):
        return f"{self.nomor_anggota} - {self.nama}"

    def set_password(self, raw_password: str):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password_hash)

    def get_total_simpanan(self):
        return self.simpanan.aggregate(
            total=Sum('jumlah')
        )['total'] or 0

    def get_total_penarikan(self):
        return self.penarikan.aggregate(
            total=Sum('jumlah')
        )['total'] or 0

    def get_saldo(self):
        return self.get_total_simpanan() - self.get_total_penarikan()