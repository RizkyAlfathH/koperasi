from django import forms
from django.db.models import Sum

from .utils import hitung_saldo
from .models import HistoryTabungan, Simpanan, Penarikan
import datetime
from datetime import date
import re


class SimpananForm(forms.ModelForm):

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

    dana_sosial = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control rupiah-input',
            'placeholder': 'Dana sosial'
        })
    )

    class Meta:
        model = Simpanan
        fields = [
            'anggota',
            'jenis_simpanan',
            'tanggal',
            'jumlah',
            'dana_sosial'
        ]
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

    # ================= INIT =================
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['tanggal'].initial = datetime.date.today()

    # ================= HELPER =================
    def _to_int(self, value):
        if not value:
            return 0
        return int(re.sub(r'\D', '', str(value)))

    # ================= VALIDASI FIELD =================
    def clean_jumlah(self):
        jumlah = self.cleaned_data.get('jumlah')
        jumlah = self._to_int(jumlah)

        if jumlah <= 0:
            raise forms.ValidationError("Jumlah simpanan harus lebih dari 0.")

        if jumlah < 1000:
            raise forms.ValidationError("Minimal simpanan Rp 1.000.")

        return jumlah

    def clean_dana_sosial(self):
        dana = self.cleaned_data.get('dana_sosial')
        dana = self._to_int(dana)

        if dana < 0:
            raise forms.ValidationError("Dana sosial tidak boleh negatif.")

        return dana

    def clean_tanggal(self):
        tanggal = self.cleaned_data.get('tanggal')

        if tanggal and tanggal > datetime.date.today():
            raise forms.ValidationError("Tanggal tidak boleh di masa depan.")

        return tanggal

    # ================= VALIDASI GLOBAL =================
    def clean(self):
        cleaned = super().clean()

        anggota = cleaned.get('anggota')
        jenis = cleaned.get('jenis_simpanan')
        tanggal = cleaned.get('tanggal')

        # pastikan dana sosial sudah dalam bentuk angka
        dana_sosial_raw = cleaned.get('dana_sosial')
        dana_sosial = self._to_int(dana_sosial_raw)

        if not anggota or not jenis or not tanggal:
            return cleaned

        # ================= SIMPANAN WAJIB =================
        if jenis.pk == 2:

            sudah_bayar = Simpanan.objects.filter(
                anggota=anggota,
                jenis_simpanan=jenis,
                tanggal__month=tanggal.month,
                tanggal__year=tanggal.year
            ).exists()

            if not sudah_bayar and dana_sosial <= 0:
                self.add_error(
                    "dana_sosial",
                    "Dana sosial wajib diisi karena simpanan wajib bulan ini belum dibayar."
                )

        else:
            # 🔥 PENTING: reset error kalau bukan jenis wajib
            self.errors.pop('dana_sosial', None)

        return cleaned

# ======================================================

class PenarikanForm(forms.ModelForm):

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

    class Meta:
        model = Penarikan
        fields = ["tanggal", "jumlah"]
        widgets = {
            "tanggal": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            ),
        }
        error_messages = {
            "tanggal": {
                "required": "Tanggal penarikan wajib diisi."
            }
        }

    def __init__(self, *args, **kwargs):
        self.anggota = kwargs.pop("anggota", None)
        self.jenis_simpanan = kwargs.pop("jenis_simpanan", None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields["tanggal"].initial = date.today()

    # ===============================
    # FORMAT RUPIAH KE ANGKA
    # ===============================
    def _to_decimal(self, value):
        if not value:
            return 0
        value = re.sub(r"[^\d]", "", value)
        return int(value) if value else 0

    # ===============================
    # VALIDASI TANGGAL
    # ===============================
    def clean_tanggal(self):
        tanggal = self.cleaned_data.get("tanggal")

        if not tanggal:
            raise forms.ValidationError("Tanggal penarikan wajib diisi.")

        if tanggal > date.today():
            raise forms.ValidationError("Tanggal tidak boleh melebihi hari ini.")

        return tanggal

    # ===============================
    # VALIDASI JUMLAH
    # ===============================
    def clean_jumlah(self):
        jumlah_input = self.cleaned_data.get("jumlah")

        if not jumlah_input:
            raise forms.ValidationError("Jumlah penarikan wajib diisi.")

        jumlah = self._to_decimal(jumlah_input)

        if jumlah <= 0:
            raise forms.ValidationError("Jumlah penarikan harus lebih dari 0.")

        # CEK SALDO
        if self.anggota and self.jenis_simpanan:
            from .utils import hitung_saldo  # pastikan ini ada
            saldo = hitung_saldo(self.anggota, self.jenis_simpanan)

            if jumlah > saldo:
                raise forms.ValidationError(
                    f"Saldo tidak mencukupi. Sisa saldo Rp {saldo:,.0f}".replace(",", ".")
                )

        return jumlah

