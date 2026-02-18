from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Anggota

User = get_user_model()

class AdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Masukkan password",
            "autocomplete": "new-password"
        }),
        required=True,
        label="Password",
        error_messages={
            "required": "Password wajib diisi."
        }
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

        self.fields["username"].required = True
        self.fields["role"].required = True

        self.fields["username"].error_messages = {
            "required": "Username wajib diisi."
        }

        self.fields["role"].error_messages = {
            "required": "Silakan pilih role."
        }

        self.fields["role"].choices = [
            ("", "---------"),
            ("ketua", "Ketua"),
            ("sekretaris", "Sekretaris"),
            ("bendahara", "Bendahara"),
        ]

    # ================= VALIDASI =================

    def clean_username(self):
        username = self.cleaned_data.get("username")

        if username and User.objects.filter(username=username).exists():
            raise ValidationError("Username sudah digunakan.")

        if username and len(username) < 4:
            raise ValidationError("Username minimal 4 karakter.")

        return username


    def clean_password(self):
        password = self.cleaned_data.get("password")

        if not password:
            raise ValidationError("Password wajib diisi.")

        if len(password) < 6:
            raise ValidationError("Password minimal 6 karakter.")

        return password

    def clean_role(self):
        role = self.cleaned_data.get("role")

        if role and role not in ["ketua", "sekretaris", "bendahara"]:
            raise ValidationError("Role tidak diizinkan.")

        return role


    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_staff = True  # otomatis staff
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

