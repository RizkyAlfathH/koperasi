from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Anggota

User = get_user_model()


# ======================================
# form admin
# ======================================
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
        labels = {
            "username": "Username",
            "role": "Jabatan"
        }
        widgets = {
            "username": forms.TextInput(attrs={
                "placeholder": "Masukkan username admin"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # pengaturan wajib isi
        self.fields["username"].required = True
        self.fields["role"].required = True

        # pesan error
        self.fields["username"].error_messages = {
            "required": "Username wajib diisi."
        }
        self.fields["role"].error_messages = {
            "required": "Jabatan wajib dipilih."
        }

        # pilihan jabatan
        self.fields["role"].choices = [
            ("", "---------"),
            ("ketua", "Ketua"),
            ("sekretaris", "Sekretaris"),
            ("bendahara", "Bendahara"),
        ]

        # mode edit
        if self.instance.pk:
            self.fields["password"].required = False
            self.fields["password"].label = "Password Baru"
            self.fields["password"].widget.attrs["placeholder"] = \
                "Masukkan password baru (opsional)"

    # validasi username
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

    # validasi password
    def clean_password(self):
        password = self.cleaned_data.get("password")

        if self.instance.pk and not password:
            return password

        if not password:
            raise ValidationError("Password wajib diisi.")

        if len(password) < 6:
            raise ValidationError("Password minimal 6 karakter.")

        return password

    # validasi role
    def clean_role(self):
        role = self.cleaned_data.get("role")

        if role and role not in ["ketua", "sekretaris", "bendahara"]:
            raise ValidationError("Jabatan tidak valid.")

        return role

    # simpan data
    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get("password")

        if password:
            user.set_password(password)

        user.is_staff = True

        if commit:
            user.save()

        return user


# ======================================
# form anggota
# ======================================
class AnggotaForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        label="Password"
    )

    class Meta:
        model = Anggota
        exclude = ["password_hash"]

        labels = {
            "nomor_anggota": "Nomor Anggota",
            "nama": "Nama Lengkap",
            "umur": "Umur",
            "nip": "NIP",
            "alamat": "Alamat",
            "no_telp": "Nomor Telepon",
            "email": "Email",
            "jenis_kelamin": "Jenis Kelamin",
            "pekerjaan": "Pekerjaan",
            "tanggal_daftar": "Tanggal Daftar",
            "status": "Status",
            "alasan_nonaktif": "Alasan Tidak Aktif",
            "tanggal_nonaktif": "Tanggal Tidak Aktif",
        }

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

        # ===============================
        # mode edit vs tambah
        # ===============================
        if self.instance.pk:
            # edit
            self.fields["password"].required = False
            self.fields["password"].label = "Password Baru"
            self.fields["password"].widget.attrs["placeholder"] = \
                "Masukkan password baru (opsional)"

            # ❗ penting: nomor anggota tidak boleh diubah
            self.fields["nomor_anggota"].disabled = True

        else:
            # tambah
            self.fields["password"].required = True
            self.fields["password"].widget.attrs["placeholder"] = \
                "Masukkan password"

        # ===============================
        # error wajib isi
        # ===============================
        for field in self.fields.values():
            if field.required:
                field.error_messages.update({
                    "required": f"{field.label} wajib diisi."
                })

        # ===============================
        # placeholder
        # ===============================
        placeholders = {
            "nomor_anggota": "Masukkan nomor anggota",
            "nama": "Masukkan nama lengkap",
            "umur": "Masukkan umur",
            "nip": "Masukkan NIP",
            "alamat": "Masukkan alamat lengkap",
            "no_telp": "Masukkan nomor telepon",
            "email": "Masukkan email aktif",
            "pekerjaan": "Masukkan pekerjaan",
        }

        for name, text in placeholders.items():
            if name in self.fields:
                self.fields[name].widget.attrs.update({
                    "placeholder": text
                })

        # format tanggal
        self.fields["tanggal_daftar"].input_formats = ["%Y-%m-%d"]
        self.fields["tanggal_nonaktif"].input_formats = ["%Y-%m-%d"]

    # ===============================
    # validasi tambahan
    # ===============================
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        alasan = cleaned_data.get("alasan_nonaktif")
        tanggal = cleaned_data.get("tanggal_nonaktif")

        if status and status.lower() == "nonaktif":
            if not alasan:
                self.add_error("alasan_nonaktif", "Alasan tidak aktif wajib diisi.")
            if not tanggal:
                self.add_error("tanggal_nonaktif", "Tanggal tidak aktif wajib diisi.")

        return cleaned_data

    # ===============================
    # simpan data
    # ===============================
    def save(self, commit=True):
        anggota = super().save(commit=False)

        password = self.cleaned_data.get("password")

        if password:
            anggota.set_password(password)

        if commit:
            anggota.save()

        return anggota