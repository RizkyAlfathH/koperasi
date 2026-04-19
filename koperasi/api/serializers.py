from rest_framework import serializers
from django.db.models import Sum
from decimal import Decimal

from anggota.models import Anggota
from simpanan.models import (
    JenisSimpanan,
    Simpanan,
    Penarikan,
    HistoryTabungan
)
from pinjaman.models import (
    Pinjaman,
    Angsuran,
    JenisPinjaman,
    KategoriJasa
)

# =========================
# AUTH
# =========================
class LoginSerializer(serializers.Serializer):
    nomor_anggota = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ResetPasswordSerializer(serializers.Serializer):
    nomor_anggota = serializers.CharField()
    password = serializers.CharField(write_only=True)

# =========================
# ANGGOTA
# =========================
class AnggotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anggota
        fields = [
            "nomor_anggota",
            "nama",
            "nip",
            "email",
            "status"
        ]


class ProfilAnggotaSerializer(serializers.ModelSerializer):
    saldo = serializers.SerializerMethodField()

    class Meta:
        model = Anggota
        fields = "__all__"

    def get_saldo(self, obj):
        return obj.get_saldo()


# =========================
# SIMPANAN
# =========================
class JenisSimpananSerializer(serializers.ModelSerializer):
    class Meta:
        model = JenisSimpanan
        fields = [
            "id",
            "nama_jenis"
        ]


class SimpananSerializer(serializers.ModelSerializer):
    anggota = serializers.StringRelatedField()
    admin = serializers.StringRelatedField()
    jenis_simpanan = JenisSimpananSerializer()
    nominal = serializers.DecimalField(
        source="jumlah",
        max_digits=18,
        decimal_places=2
    )

    class Meta:
        model = Simpanan
        fields = [
            "id",
            "anggota",
            "admin",
            "jenis_simpanan",
            "tanggal",
            "nominal",
            "dana_sosial"
        ]


class PenarikanSerializer(serializers.ModelSerializer):
    anggota = serializers.StringRelatedField()
    admin = serializers.StringRelatedField()
    jenis_simpanan = JenisSimpananSerializer()
    nominal = serializers.DecimalField(
        source="jumlah",
        max_digits=18,
        decimal_places=2
    )

    class Meta:
        model = Penarikan
        fields = [
            "id",
            "anggota",
            "admin",
            "jenis_simpanan",
            "tanggal",
            "nominal"
        ]


class HistoryTabunganSerializer(serializers.ModelSerializer):
    jenis_simpanan = JenisSimpananSerializer()

    class Meta:
        model = HistoryTabungan
        fields = [
            "id",
            "jenis_simpanan",
            "tanggal",
            "jenis_transaksi",
            "jumlah"
        ]


# =========================
# PINJAMAN
# =========================
class JenisPinjamanSerializer(serializers.ModelSerializer):
    class Meta:
        model = JenisPinjaman
        fields = [
            "id_jenis_pinjaman",
            "nama_jenis"
        ]


class KategoriJasaSerializer(serializers.ModelSerializer):
    class Meta:
        model = KategoriJasa
        fields = [
            "id_kategori_jasa",
            "kategori_jasa"
        ]


# =========================
# ANGSURAN
# =========================
class AngsuranSerializer(serializers.ModelSerializer):
    admin = serializers.StringRelatedField(source="id_admin")
    nominal = serializers.DecimalField(
        source="jumlah_bayar",
        max_digits=18,
        decimal_places=2
    )

    class Meta:
        model = Angsuran
        fields = [
            "id_pembayaran",
            "admin",
            "tanggal_bayar",
            "nominal",
            "tipe_bayar"
        ]


# =========================
# PINJAMAN (NESTED FIXED)
# =========================
class PinjamanSerializer(serializers.ModelSerializer):
    anggota = serializers.StringRelatedField(source="nomor_anggota")
    jenis_pinjaman = JenisPinjamanSerializer(source="id_jenis_pinjaman")
    kategori_pinjaman = KategoriJasaSerializer(source="id_kategori_jasa")

    # ✅ Nested angsuran
    angsuran = AngsuranSerializer(
        source="angsuran_set",
        many=True,
        read_only=True
    )

    cicilan_terbayar = serializers.SerializerMethodField()
    sisa_pinjaman_real = serializers.SerializerMethodField()

    class Meta:
        model = Pinjaman
        fields = [
            "id_pinjaman",
            "anggota",
            "jumlah_pinjaman",
            "angsuran_per_bulan",
            "jasa_persen",
            "jasa_rupiah",
            "status",
            "tanggal_meminjam",
            "jatuh_tempo",
            "jenis_pinjaman",
            "kategori_pinjaman",
            "angsuran",
            "cicilan_terbayar",
            "sisa_pinjaman_real"
        ]

    def get_cicilan_terbayar(self, obj):
        return Angsuran.objects.filter(
            id_pinjaman=obj,
            tipe_bayar="cicilan"
        ).count()

    def get_sisa_pinjaman_real(self, obj):
        total_bayar = Angsuran.objects.filter(
            id_pinjaman=obj,
            tipe_bayar="cicilan"
        ).aggregate(total=Sum("jumlah_bayar"))["total"] or Decimal("0")

        sisa = obj.jumlah_pinjaman - total_bayar
        return max(sisa, Decimal("0"))