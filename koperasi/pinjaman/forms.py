from django import forms
from decimal import Decimal
from .models import Pinjaman


class PinjamanForm(forms.ModelForm):

    # ================= FIELD STRING (INPUT RUPIAH) =================
    jumlah_pinjaman = forms.CharField(
        required=True,
        error_messages={
            "required": "Jumlah pinjaman wajib diisi."
        },
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masukkan jumlah pinjaman'
        })
    )

    angsuran_per_bulan = forms.CharField(
        required=True,
        error_messages={
            "required": "Angsuran per bulan wajib diisi."
        },
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masukkan jumlah angsuran per bulan'
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

        error_messages = {
            'nomor_anggota': {
                'required': 'Nama Anggota wajib diisi.'
            },
            'id_jenis_pinjaman': {
                'required': 'Jenis Pinjaman wajib dipilih.'
            },
            'tanggal_meminjam': {
                'required': 'Tanggal Pinjam wajib diisi.'
            },
            'jatuh_tempo': {
                'required': 'Lama Pinjaman wajib diisi.'
            },
        }

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
                'placeholder': 'Masukkan jumlah bulan (1-36)'
            }),

            'jasa_persen': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Contoh: 1,5'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if field.required and "required" not in field.error_messages:
                field.error_messages["required"] = f"{field.label} wajib diisi."

    # ================= HELPER =================
    def _rupiah_to_decimal(self, value):
        if not value:
            return None

        try:
            return Decimal(
                value.replace('Rp', '')
                    .replace('.', '')
                    .replace(',', '')
                    .strip()
            )
        except:
            raise forms.ValidationError("Format rupiah tidak valid.")

    # ================= CLEAN PER FIELD =================
    def clean_jatuh_tempo(self):
        jatuh_tempo = self.cleaned_data.get("jatuh_tempo")

        if jatuh_tempo and (jatuh_tempo < 1 or jatuh_tempo > 36):
            raise forms.ValidationError(
                "Lama pinjaman harus antara 1 sampai 36 bulan."
            )

        return jatuh_tempo
    
    def clean_jumlah_pinjaman(self):
        raw = self.cleaned_data.get('jumlah_pinjaman')

        if not raw:
            raise forms.ValidationError("Jumlah pinjaman wajib diisi.")

        value = self._rupiah_to_decimal(raw)

        if value <= 0:
            raise forms.ValidationError(
                "Jumlah pinjaman harus lebih dari 0."
            )

        return value

    def clean_angsuran_per_bulan(self):
        value = self._rupiah_to_decimal(
            self.cleaned_data.get('angsuran_per_bulan')
        )

        if value <= 0:
            raise forms.ValidationError(
                "Angsuran per bulan harus lebih dari 0."
            )

        return value

    def clean_jasa_rupiah(self):
        return self._rupiah_to_decimal(
            self.cleaned_data.get('jasa_rupiah')
        )

    def clean_jasa_persen(self):
        jasa_persen = self.cleaned_data.get('jasa_persen')

        if jasa_persen is None:
            raise forms.ValidationError("Persentase jasa wajib diisi.")

        if jasa_persen < 0:
            raise forms.ValidationError("Persentase tidak boleh minus.")

        if jasa_persen > 100:
            raise forms.ValidationError("Persentase tidak boleh lebih dari 100%.")

        return jasa_persen

    # ================= CLEAN GLOBAL =================
    def clean(self):
        cleaned_data = super().clean()

        jumlah = cleaned_data.get('jumlah_pinjaman')
        persen = cleaned_data.get('jasa_persen')

        if jumlah and persen is not None:
            if persen < 0:
                self.add_error("jasa_persen", "Persentase tidak boleh minus.")

            jasa = jumlah * (persen / Decimal('100'))
            cleaned_data['jasa_rupiah'] = jasa.quantize(Decimal('1'))

        return cleaned_data