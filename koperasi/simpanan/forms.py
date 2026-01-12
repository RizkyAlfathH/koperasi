from django import forms
from django.db.models import Sum

from .utils import hitung_saldo
from .models import HistoryTabungan, Simpanan, Penarikan
import datetime
import re


class SimpananForm(forms.ModelForm):
    jumlah = forms.CharField(
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
            'anggota': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cari anggota'
            }),
            'tanggal': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'jenis_simpanan': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['tanggal'].initial = datetime.date.today()

    def _to_int(self, value):
        if not value:
            return 0
        return int(re.sub(r'\D', '', value))

    def clean_jumlah(self):
        jumlah = self.cleaned_data.get('jumlah')
        jumlah = self._to_int(jumlah)

        if jumlah <= 0:
            raise forms.ValidationError("Jumlah simpanan harus lebih dari 0.")

        return jumlah

    def clean_dana_sosial(self):
        dana = self.cleaned_data.get('dana_sosial')
        return self._to_int(dana)

    def clean(self):
        cleaned = super().clean()

        anggota = cleaned.get('anggota')
        jenis = cleaned.get('jenis_simpanan')
        tanggal = cleaned.get('tanggal')
        dana_sosial = cleaned.get('dana_sosial', 0)

        if not anggota or not jenis or not tanggal:
            return cleaned

        if jenis.pk == 2:
            sudah_bayar = Simpanan.objects.filter(
                anggota=anggota,
                jenis_simpanan=jenis,
                tanggal__month=tanggal.month,
                tanggal__year=tanggal.year
            ).exists()

            if not sudah_bayar and dana_sosial <= 0:
                raise forms.ValidationError(
                    "Dana sosial wajib diisi karena simpanan wajib bulan ini belum dibayar."
                )

        return cleaned

# ======================================================

class PenarikanForm(forms.ModelForm):
    class Meta:
        model = Penarikan
        fields = ["tanggal", "jumlah"]
        widgets = {
            "tanggal": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control datepicker"
                },
                format="%Y-%m-%d"
            ),
        }

    def __init__(self, *args, **kwargs):
        self.anggota = kwargs.pop("anggota", None)
        self.jenis_simpanan = kwargs.pop("jenis_simpanan", None)
        super().__init__(*args, **kwargs)

        # ⬅️ samain dengan SimpananForm
        if not self.instance.pk:
            self.fields["tanggal"].initial = datetime.date.today()

    def clean_jumlah(self):
        jumlah = self.cleaned_data.get("jumlah")

        if jumlah <= 0:
            raise forms.ValidationError("Jumlah penarikan harus lebih dari 0")

        if self.anggota and self.jenis_simpanan:
            saldo = hitung_saldo(self.anggota, self.jenis_simpanan)
            if jumlah > saldo:
                raise forms.ValidationError(
                    f"Saldo tidak mencukupi. Sisa saldo Rp {saldo:,.0f}"
                )

        return jumlah

