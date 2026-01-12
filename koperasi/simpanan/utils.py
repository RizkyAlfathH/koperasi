from django.db.models import Sum
from .models import HistoryTabungan

def hitung_saldo(anggota, jenis_simpanan):
    setor = HistoryTabungan.objects.filter(
        anggota=anggota,
        jenis_simpanan=jenis_simpanan,
        jenis_transaksi="SETOR"
    ).aggregate(total=Sum("jumlah"))["total"] or 0

    tarik = HistoryTabungan.objects.filter(
        anggota=anggota,
        jenis_simpanan=jenis_simpanan,
        jenis_transaksi="TARIK"
    ).aggregate(total=Sum("jumlah"))["total"] or 0

    return setor - tarik
