from django.contrib.auth.models import AbstractUser
from django.db import models

# class (model) User turunan dari AbstractUser
class User(AbstractUser):

    # atribut class (konstanta) untuk pilihan role
    ROLE_CHOICES = (
        ('admin', 'Administrator Sistem'),
        ('ketua', 'Ketua'),
        ('sekretaris', 'Sekretaris'),
        ('bendahara', 'Bendahara'),
    )

    # field database (objek dari class CharField)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    # method (fungsi di dalam class)
    def __str__(self):
        # mengembalikan representasi string dari objek User
        return f"{self.username} - {self.role}"


# class (model) untuk menyimpan hak akses role
class RolePermission(models.Model):

    # field database
    role = models.CharField(max_length=20)
    permission_code = models.CharField(max_length=50)

    # class Meta (class di dalam model untuk konfigurasi tambahan)
    class Meta:
        # constraint database (kombinasi role + permission tidak boleh duplikat)
        unique_together = ('role', 'permission_code')

    # method untuk representasi string objek
    def __str__(self):
        return f"{self.role} - {self.permission_code}"
