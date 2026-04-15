# koperasi/pinjaman/management/commands/auto_bayar_sukarela.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pinjaman.models import Pinjaman
from pinjaman.utils import cek_auto_sukarela_ke_pinjaman  # ← WAJIB dari utils

User = get_user_model()

class Command(BaseCommand):
    help = "Auto bayar cicilan dari simpanan sukarela (dijalankan tiap tgl 1)"

    def handle(self, *args, **kwargs):
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stderr.write("Tidak ada superuser ditemukan.")
            return

        pinjaman_aktif = Pinjaman.objects.filter(status="Aktif")
        total = 0

        for pinjaman in pinjaman_aktif:
            cek_auto_sukarela_ke_pinjaman(pinjaman, admin)
            total += 1

        self.stdout.write(
            self.style.SUCCESS(f"Auto bayar selesai: {total} pinjaman diproses.")
        )