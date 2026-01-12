from django import forms
from decimal import Decimal
from .models import Pinjaman


class PinjamanForm(forms.ModelForm):
    class Meta:
        model = Pinjaman
        fields = [
            'nomor_anggota',
            'id_jenis_pinjaman',
            'id_kategori_jasa',
            'tanggal_meminjam',
            'jatuh_tempo',
            'jumlah_pinjaman',
            'angsuran_per_bulan',
            'jasa_persen',
            'jasa_rupiah',
        ]

        widgets = {
            'nomor_anggota': forms.Select(attrs={'class': 'form-control select2'}),
            'id_jenis_pinjaman': forms.Select(attrs={'class': 'form-control'}),
            'id_kategori_jasa': forms.Select(attrs={'class': 'form-control'}),

            'tanggal_meminjam': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),

            'jatuh_tempo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 36,
                'placeholder': 'Lama pinjaman (bulan)'
            }),

            'jumlah_pinjaman': forms.TextInput(attrs={'class': 'form-control'}),
            'angsuran_per_bulan': forms.TextInput(attrs={'class': 'form-control'}),

            'jasa_persen': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),

            'jasa_rupiah': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
        }

    def clean_jumlah_pinjaman(self):
        value = self.cleaned_data.get('jumlah_pinjaman')
        return Decimal(str(value).replace('.', '').replace(',', ''))

    def clean_angsuran_per_bulan(self):
        value = self.cleaned_data.get('angsuran_per_bulan')
        return Decimal(str(value).replace('.', '').replace(',', ''))

    def clean(self):
        cleaned = super().clean()
        jumlah = cleaned.get('jumlah_pinjaman')
        persen = cleaned.get('jasa_persen')

        if jumlah and persen:
            cleaned['jasa_rupiah'] = jumlah * persen / Decimal('100')

        return cleaned
