from django import forms
from django.db.models import Sum

from .utils import hitung_saldo
from .models import HistoryTabungan, Simpanan, Penarikan
import datetime
from datetime import date
import re


# class: form berbasis model untuk input data simpanan
class SimpananForm(forms.ModelForm):

    # field (form): input jumlah simpanan dalam bentuk string (format rupiah)
    jumlah = forms.CharField(
        required=True,
        error_messages={
            "required": "Jumlah simpanan wajib diisi."
        },
        widget=forms.TextInput(attrs={
            'class': 'form-control rupiah-input',
            'placeholder': 'Masukkan jumlah simpanan'
        })
    )

    # field (form): input dana sosial (opsional)
    dana_sosial = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control rupiah-input',
            'placeholder': 'Dana sosial'
        })
    )

    # class meta: konfigurasi model yang digunakan oleh form
    class Meta:
        model = Simpanan  # objek model yang digunakan
        fields = [
            'anggota',
            'jenis_simpanan',
            'tanggal',
            'jumlah',
            'dana_sosial'
        ]

        # widget: pengaturan tampilan input pada form
        widgets = {
            'anggota': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tanggal': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'jenis_simpanan': forms.Select(attrs={'class': 'form-control'}),
        }

        # pesan error untuk field tertentu
        error_messages = {
            'anggota': {
                'required': 'Nama anggota wajib diisi.'
            },
            'jenis_simpanan': {
                'required': 'Jenis simpanan wajib dipilih.'
            },
            'tanggal': {
                'required': 'Tanggal wajib diisi.'
            }
        }

    # method: constructor untuk inisialisasi form
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # kondisi: jika data baru (bukan edit)
        if not self.instance.pk:
            # set default tanggal hari ini
            self.fields['tanggal'].initial = datetime.date.today()

    # method (helper): konversi string ke integer (hapus karakter non-angka)
    def _to_int(self, value):
        if not value:
            return 0
        return int(re.sub(r'\D', '', str(value)))

    # method: validasi field jumlah
    def clean_jumlah(self):
        jumlah = self.cleaned_data.get('jumlah')

        # proses: konversi ke integer
        jumlah = self._to_int(jumlah)

        # validasi: harus lebih dari 0
        if jumlah <= 0:
            raise forms.ValidationError("Jumlah simpanan harus lebih dari 0.")

        # validasi: minimal nominal
        if jumlah < 1000:
            raise forms.ValidationError("Minimal simpanan Rp 1.000.")

        return jumlah

    # method: validasi field dana sosial
    def clean_dana_sosial(self):
        dana = self.cleaned_data.get('dana_sosial')

        # proses: konversi ke integer
        dana = self._to_int(dana)

        # validasi: tidak boleh negatif
        if dana < 0:
            raise forms.ValidationError("Dana sosial tidak boleh negatif.")

        return dana

    # method: validasi field tanggal
    def clean_tanggal(self):
        tanggal = self.cleaned_data.get('tanggal')

        # validasi: tidak boleh di masa depan
        if tanggal and tanggal > datetime.date.today():
            raise forms.ValidationError("Tanggal tidak boleh di masa depan.")

        return tanggal

    # method: validasi global (antar field)
    def clean(self):
        cleaned = super().clean()

        # ambil data dari form
        anggota = cleaned.get('anggota')
        jenis = cleaned.get('jenis_simpanan')
        tanggal = cleaned.get('tanggal')

        # ambil dana sosial dan konversi ke angka
        dana_sosial_raw = cleaned.get('dana_sosial')
        dana_sosial = self._to_int(dana_sosial_raw)

        # jika ada field kosong, hentikan validasi lanjutan
        if not anggota or not jenis or not tanggal:
            return cleaned

        # logika: jika jenis simpanan wajib
        if jenis.pk == 2:

            # cek apakah sudah bayar bulan ini
            sudah_bayar = Simpanan.objects.filter(
                anggota=anggota,
                jenis_simpanan=jenis,
                tanggal__month=tanggal.month,
                tanggal__year=tanggal.year
            ).exists()

            # jika belum bayar dan dana sosial kosong
            if not sudah_bayar and dana_sosial <= 0:
                self.add_error(
                    "dana_sosial",
                    "Dana sosial wajib diisi karena simpanan wajib bulan ini belum dibayar."
                )

        else:
            # jika bukan simpanan wajib, hapus error dana sosial jika ada
            self.errors.pop('dana_sosial', None)

        return cleaned


# class: form berbasis model untuk proses penarikan simpanan
class PenarikanForm(forms.ModelForm):

    # field (form): input jumlah penarikan dalam bentuk string (format rupiah)
    jumlah = forms.CharField(
        required=True,
        label="Jumlah Penarikan",
        error_messages={
            "required": "Jumlah penarikan wajib diisi."
        },
        widget=forms.TextInput(attrs={
            "class": "form-control rupiah-input",
            "placeholder": "Masukkan jumlah penarikan"
        })
    )

    # class meta: konfigurasi model yang digunakan oleh form
    class Meta:
        model = Penarikan  # objek model yang digunakan
        fields = ["tanggal", "jumlah"]

        # widget: pengaturan tampilan field
        widgets = {
            "tanggal": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            ),
        }

        # error message untuk field tertentu
        error_messages = {
            "tanggal": {
                "required": "Tanggal penarikan wajib diisi."
            }
        }

    # method: constructor untuk inisialisasi form
    def __init__(self, *args, **kwargs):
        # ambil parameter tambahan (bukan dari model/form default)
        self.anggota = kwargs.pop("anggota", None)          # objek anggota
        self.jenis_simpanan = kwargs.pop("jenis_simpanan", None)  # objek jenis simpanan

        super().__init__(*args, **kwargs)

        # kondisi: jika data baru (bukan edit)
        if not self.instance.pk:
            # set default tanggal hari ini
            self.fields["tanggal"].initial = date.today()

    # method (helper): konversi format rupiah ke angka integer
    def _to_decimal(self, value):
        if not value:
            return 0

        # proses: hapus semua karakter selain angka
        value = re.sub(r"[^\d]", "", value)

        # return hasil konversi
        return int(value) if value else 0

    # method: validasi field tanggal
    def clean_tanggal(self):
        tanggal = self.cleaned_data.get("tanggal")

        # validasi: wajib diisi
        if not tanggal:
            raise forms.ValidationError("Tanggal penarikan wajib diisi.")

        # validasi: tidak boleh lebih dari hari ini
        if tanggal > date.today():
            raise forms.ValidationError("Tanggal tidak boleh melebihi hari ini.")

        return tanggal

    # method: validasi field jumlah penarikan
    def clean_jumlah(self):
        jumlah_input = self.cleaned_data.get("jumlah")

        # validasi: wajib diisi
        if not jumlah_input:
            raise forms.ValidationError("Jumlah penarikan wajib diisi.")

        # proses: konversi ke angka
        jumlah = self._to_decimal(jumlah_input)

        # validasi: harus lebih dari 0
        if jumlah <= 0:
            raise forms.ValidationError("Jumlah penarikan harus lebih dari 0.")

        # validasi tambahan: cek saldo anggota
        if self.anggota and self.jenis_simpanan:
            from .utils import hitung_saldo  # fungsi helper (fungsi eksternal)

            # ambil saldo berdasarkan anggota dan jenis simpanan
            saldo = hitung_saldo(self.anggota, self.jenis_simpanan)

            # validasi: jumlah tidak boleh melebihi saldo
            if jumlah > saldo:
                raise forms.ValidationError(
                    f"Saldo tidak mencukupi. Sisa saldo Rp {saldo:,.0f}".replace(",", ".")
                )

        return jumlah