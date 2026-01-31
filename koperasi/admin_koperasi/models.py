from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator Sistem'),
        ('ketua', 'Ketua'),
        ('sekretaris', 'Sekretaris'),
        ('bendahara', 'Bendahara'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    def __str__(self):
        return f"{self.username} - {self.role}"

# admin_koperasi/models.py

class RolePermission(models.Model):
    role = models.CharField(max_length=20)
    permission_code = models.CharField(max_length=50)

    class Meta:
        unique_together = ('role', 'permission_code')

    def __str__(self):
        return f"{self.role} - {self.permission_code}"
