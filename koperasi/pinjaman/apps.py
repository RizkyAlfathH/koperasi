# koperasi/pinjaman/apps.py

from django.apps import AppConfig

class PinjamanConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pinjaman"

    # def ready(self):
    #     import sys
    #     # Jangan jalankan saat perintah migrate, makemigrations, shell, dll
    #     excluded = ("migrate", "makemigrations", "shell", "test", "collectstatic")
    #     if any(cmd in sys.argv for cmd in excluded):
    #         return
    #     from . import scheduler
    #     scheduler.start()