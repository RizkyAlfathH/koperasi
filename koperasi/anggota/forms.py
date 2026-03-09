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

    # ================= INIT =================
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

        # ================= MODE EDIT =================
        if self.instance.pk:

            # password tidak wajib
            self.fields["password"].required = False

            # ubah label
            self.fields["password"].label = "Password Baru"

            # ubah placeholder
            self.fields["password"].widget.attrs["placeholder"] = \
                "Masukkan password baru (opsional)"

    # ================= VALIDASI =================

    def clean_username(self):
        username = self.cleaned_data.get("username")

        if not username:
            return username

        qs = User.objects.filter(username=username)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("Username sudah digunakan.")

        if len(username) < 4:
            raise ValidationError("Username minimal 4 karakter.")

        return username

    def clean_password(self):
        password = self.cleaned_data.get("password")

        # jika edit dan kosong → tidak diubah
        if self.instance.pk and not password:
            return password

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

    # ================= SAVE =================

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get("password")

        # hanya update password jika diisi
        if password:
            user.set_password(password)

        user.is_staff = True

        if commit:
            user.save()

        return user


class AnggotaForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        label="Password Baru"
    )

    class Meta:
        model = Anggota
        exclude = ["password_hash"]
        widgets = {
            "tanggal_daftar": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"}
            ),
            "tanggal_nonaktif": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if field.required:
                field.error_messages.update({
                    "required": f"{field.label} wajib diisi."
                })


        # ===============================
        # PLACEHOLDER
        # ===============================
        self.fields["nomor_anggota"].widget.attrs.update({
            "placeholder": "Masukkan Nomor anggota",
            "inputmode": "numeric"
        })
        self.fields["nama"].widget.attrs.update({
            "placeholder": "Masukkan Nama lengkap"
        })
        self.fields["umur"].widget.attrs.update({
            "placeholder": "Masukkan Umur"
        })
        self.fields["nip"].widget.attrs.update({
            "placeholder": "Masukkan NIP"
        })
        self.fields["alamat"].widget.attrs.update({
            "placeholder": "Masukkan Alamat lengkap"
        })
        self.fields["no_telp"].widget.attrs.update({
            "placeholder": "Masukkan Nomor telepon"
        })
        self.fields["email"].widget.attrs.update({
            "placeholder": "Masukkan Email aktif"
        })
        self.fields["pekerjaan"].widget.attrs.update({
            "placeholder": "Masukkan Pekerjaan"
        })
        self.fields["tanggal_daftar"].input_formats = ["%Y-%m-%d"]
        self.fields["tanggal_nonaktif"].input_formats = ["%Y-%m-%d"]

        if not self.instance.pk:
            self.fields["password"].required = True

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        alasan = cleaned_data.get("alasan_nonaktif")
        tanggal = cleaned_data.get("tanggal_nonaktif")

        if status and status.lower() == "nonaktif":
            if not alasan:
                self.add_error("alasan_nonaktif", "Alasan nonaktif wajib diisi.")
            if not tanggal:
                self.add_error("tanggal_nonaktif", "Tanggal nonaktif wajib diisi.")

        return cleaned_data

    def save(self, commit=True):
        anggota = super().save(commit=False)

        password = self.cleaned_data.get("password")
        if password:
            anggota.set_password(password)

        if commit:
            anggota.save()
        return anggota

