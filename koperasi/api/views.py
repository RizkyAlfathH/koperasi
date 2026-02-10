from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from .serializers import (
    LoginSerializer,
    AnggotaSerializer,
    ResetPasswordSerializer,
    SimpananSerializer,
    PenarikanSerializer,
    PinjamanSerializer,
    AngsuranSerializer,
    ProfilAnggotaSerializer
)

from anggota.models import Anggota
from simpanan.models import Simpanan, Penarikan
from pinjaman.models import Pinjaman, Angsuran


# ==========================
# AUTH & AKUN ANGGOTA
# ==========================
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        nomor_anggota = serializer.validated_data["nomor_anggota"]
        password = serializer.validated_data["password"]

        try:
            anggota = Anggota.objects.get(
                nomor_anggota=nomor_anggota,
                status="aktif"
            )
        except Anggota.DoesNotExist:
            return Response(
                {"error": "Nomor anggota tidak ditemukan atau akun nonaktif"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not anggota.check_password(password):
            return Response(
                {"error": "Password salah"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = AnggotaSerializer(anggota).data
        return Response(
            {"message": "Login berhasil", "data": data},
            status=status.HTTP_200_OK
        )


class CheckNomorAnggotaView(APIView):
    def post(self, request):
        nomor_anggota = request.data.get("nomor_anggota")

        if not nomor_anggota:
            return Response(
                {"error": "Nomor anggota wajib diisi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        exists = Anggota.objects.filter(
            nomor_anggota=nomor_anggota
        ).exists()

        return Response({"exists": exists}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        nomor_anggota = serializer.validated_data["nomor_anggota"]
        new_password = serializer.validated_data["password"]

        try:
            anggota = Anggota.objects.get(
                nomor_anggota=nomor_anggota,
                status="aktif"
            )
        except Anggota.DoesNotExist:
            return Response(
                {"error": "Nomor anggota tidak ditemukan atau akun nonaktif"},
                status=status.HTTP_404_NOT_FOUND
            )

        anggota.set_password(new_password)
        anggota.save()

        return Response(
            {"message": "Password berhasil direset"},
            status=status.HTTP_200_OK
        )


# ==========================
# SIMPANAN
# ==========================
class SimpananListView(APIView):
    def get(self, request, nomor_anggota):
        simpanan = Simpanan.objects.filter(
            anggota__nomor_anggota=nomor_anggota
        )  # ordering sudah dari model (-tanggal)

        serializer = SimpananSerializer(simpanan, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# PENARIKAN
# ==========================
class PenarikanListView(APIView):
    def get(self, request, nomor_anggota):
        penarikan = Penarikan.objects.filter(
            anggota__nomor_anggota=nomor_anggota
        )  # ordering dari model (-tanggal)

        serializer = PenarikanSerializer(penarikan, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# PINJAMAN
# ==========================
class PinjamanListView(APIView):
    def get(self, request, nomor_anggota):
        pinjaman = Pinjaman.objects.filter(
            nomor_anggota__nomor_anggota=nomor_anggota
        ).order_by("-tanggal_meminjam")

        serializer = PinjamanSerializer(pinjaman, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# ANGSURAN
# ==========================
class AngsuranListView(APIView):
    def get(self, request, id_pinjaman):
        angsuran = Angsuran.objects.filter(
            id_pinjaman=id_pinjaman
        ).order_by("-tanggal_bayar")

        serializer = AngsuranSerializer(angsuran, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================
# PROFIL ANGGOTA
# ==========================
class ProfilAnggotaView(APIView):
    def get(self, request, nomor_anggota):
        clean = nomor_anggota.strip().replace(" ", "")

        if not clean:
            return Response(
                {"detail": "NIP atau Nomor Anggota tidak boleh kosong"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            anggota = Anggota.objects.get(
                Q(nip=nomor_anggota) |
                Q(nomor_anggota=nomor_anggota) |
                Q(nip=clean) |
                Q(nomor_anggota=clean)
            )
        except Anggota.DoesNotExist:
            return Response(
                {"detail": "Anggota tidak ditemukan"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProfilAnggotaSerializer(anggota)
        return Response(serializer.data, status=status.HTTP_200_OK)