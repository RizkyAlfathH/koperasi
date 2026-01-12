from django import forms
from django.contrib.auth import get_user_model
from .models import Anggota

User = get_user_model()

class AdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Masukkan password",
            "autocomplete": "new-password"
        }),
        required=False,
        label="Password"
    )

    class Meta:
        model = User
        fields = ["username", "role"]

        widgets = {
            "username": forms.TextInput(attrs={
                "placeholder": "Username admin"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ROLE DROPDOWN (EMPTY DEFAULT)
        self.fields["role"].choices = [
            ("", "---------"),
            ("ketua", "Ketua"),
            ("sekretaris", "Sekretaris"),
            ("bendahara", "Bendahara"),
        ]

        self.fields["role"].required = True

        # OPTIONAL: styling konsisten
        self.fields["role"].widget.attrs.update({
            "class": "form-control"
        })

    def clean_role(self):
        role = self.cleaned_data.get("role")

        if not role:
            raise forms.ValidationError("Silakan pilih role.")

        if role not in ["ketua", "sekretaris", "bendahara"]:
            raise forms.ValidationError("Role tidak diizinkan.")

        return role

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)

        if commit:
            user.save()

        return user


class AnggotaForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Masukkan password",
            "autocomplete": "new-password"
        }),
        required=False,
        label="Password"
    )

    class Meta:
        model = Anggota
        fields = [
            "nomor_anggota",
            "nama",
            "umur",
            "nip",
            "alamat",
            "no_telp",
            "email",
            "jenis_kelamin",
            "pekerjaan",
            "tanggal_daftar",
            "status",
            "alasan_nonaktif",
            "tanggal_nonaktif",
        ]

        widgets = {
            "tanggal_daftar": forms.DateInput(attrs={
                "type": "date",
                "placeholder": "Tanggal daftar"
            }),
            "tanggal_nonaktif": forms.DateInput(attrs={
                "type": "date",
                "placeholder": "Tanggal nonaktif"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["nomor_anggota"].widget.attrs.update({
            "placeholder": "Nomor anggota",
            "inputmode": "numeric"
        })
        self.fields["nama"].widget.attrs.update({
            "placeholder": "Nama lengkap"
        })
        self.fields["umur"].widget.attrs.update({
            "placeholder": "Umur"
        })
        self.fields["nip"].widget.attrs.update({
            "placeholder": "NIP"
        })
        self.fields["alamat"].widget.attrs.update({
            "placeholder": "Alamat lengkap"
        })
        self.fields["no_telp"].widget.attrs.update({
            "placeholder": "Nomor telepon"
        })
        self.fields["email"].widget.attrs.update({
            "placeholder": "Email aktif"
        })
        self.fields["pekerjaan"].widget.attrs.update({
            "placeholder": "Pekerjaan"
        })

    def save(self, commit=True):
        anggota = super().save(commit=False)

        password = self.cleaned_data.get("password")
        if password:
            anggota.set_password(password)

        if commit:
            anggota.save()
        return anggota

