# koperasi/pinjaman/scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def jalankan_auto_bayar():
    """Fungsi yang dipanggil scheduler tiap tgl 1 jam 00:05."""
    logger.info("Scheduler: menjalankan auto_bayar_sukarela...")
    call_command("auto_bayar_sukarela")

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        jalankan_auto_bayar,
        trigger=CronTrigger(day=1, hour=0, minute=5),  # Tiap tgl 1, jam 00:05
        id="auto_bayar_sukarela",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler auto bayar sukarela aktif.")