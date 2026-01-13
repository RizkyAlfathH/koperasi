from django import forms
from decimal import Decimal
from .models import Pinjaman


class PinjamanForm(forms.ModelForm):

    # ================= FIELD STRING (INPUT RUPIAH) =================
    jumlah_pinjaman = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Jumlah pinjaman'
        })
    )

    angsuran_per_bulan = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Angsuran per bulan'
        })
    )

    jasa_rupiah = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )

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

            'jasa_persen': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Persentase jasa'
            }),
        }

    # ================= HELPER =================
    def _rupiah_to_decimal(self, value):
        """
        'Rp 1.000.000' -> Decimal('1000000')
        """
        if not value:
            return Decimal('0')

        return Decimal(
            value.replace('Rp', '')
                 .replace('.', '')
                 .replace(',', '')
                 .strip()
        )

    # ================= CLEAN PER FIELD =================
    def clean_jumlah_pinjaman(self):
        return self._rupiah_to_decimal(
            self.cleaned_data.get('jumlah_pinjaman')
        )

    def clean_angsuran_per_bulan(self):
        return self._rupiah_to_decimal(
            self.cleaned_data.get('angsuran_per_bulan')
        )

    def clean_jasa_rupiah(self):
        return self._rupiah_to_decimal(
            self.cleaned_data.get('jasa_rupiah')
        )

    def clean_jasa_persen(self):
        jasa_persen = self.cleaned_data.get('jasa_persen')

        if jasa_persen is None:
            return jasa_persen

        try:
            return Decimal(str(jasa_persen).replace(',', '.'))
        except Exception:
            raise forms.ValidationError(
                "Persentase jasa tidak valid, gunakan format angka."
            )

    # ================= CLEAN GLOBAL =================
    def clean(self):
        cleaned_data = super().clean()

        jumlah = cleaned_data.get('jumlah_pinjaman')   # Decimal
        persen = cleaned_data.get('jasa_persen')       # Decimal

        if jumlah and persen is not None:
            jasa = jumlah * (persen / Decimal('100'))
            cleaned_data['jasa_rupiah'] = jasa.quantize(Decimal('1'))

        return cleaned_data