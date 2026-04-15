from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, EmailValidator
from django.contrib.auth import get_user_model
from .models import Anggota

User = get_user_model()


# form admin (class berbasis ModelForm)
class AdminForm(forms.ModelForm):

    # field tambahan (objek dari forms.CharField)
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

    # class Meta (konfigurasi model form)
    class Meta:
        model = User  # relasi ke model User
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

    # method constructor (dipanggil saat objek form dibuat)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # pengaturan wajib isi
        self.fields["username"].required = True
        self.fields["role"].required = True

        # pengaturan pesan error
        self.fields["username"].error_messages = {
            "required": "Username wajib diisi."
        }
        self.fields["role"].error_messages = {
            "required": "Jabatan wajib dipilih."
        }

        # pengaturan pilihan role
        self.fields["role"].choices = [
            ("", "Pilih Jabatan"),
            ("ketua", "Ketua"),
            ("sekretaris", "Sekretaris"),
            ("bendahara", "Bendahara"),
        ]

        # kondisi mode edit (jika instance sudah ada di database)
        if self.instance.pk:
            self.fields["password"].required = False
            self.fields["password"].label = "Password Baru"
            self.fields["password"].widget.attrs["placeholder"] = \
                "Masukkan password baru (opsional)"

    # method validasi username
    def clean_username(self):
        username = self.cleaned_data.get("username")

        if not username:
            return username

        # query ORM (objek queryset)
        qs = User.objects.filter(username=username)

        # jika edit, exclude data sendiri
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        # validasi duplikat
        if qs.exists():
            raise ValidationError("Username sudah digunakan.")

        # validasi panjang karakter
        if len(username) < 4:
            raise ValidationError("Username minimal 4 karakter.")

        return username

    # method validasi password
    def clean_password(self):
        password = self.cleaned_data.get("password")

        # jika edit dan password kosong → boleh
        if self.instance.pk and not password:
            return password

        if not password:
            raise ValidationError("Password wajib diisi.")

        if len(password) < 6:
            raise ValidationError("Password minimal 6 karakter.")

        return password

    # method validasi role
    def clean_role(self):
        role = self.cleaned_data.get("role")

        # validasi nilai role
        if role and role not in ["ketua", "sekretaris", "bendahara"]:
            raise ValidationError("Jabatan tidak valid.")

        return role

    # method untuk menyimpan data
    def save(self, commit=True):
        user = super().save(commit=False)  # objek model User

        password = self.cleaned_data.get("password")

        # set password terenkripsi
        if password:
            user.set_password(password)

        user.is_staff = True

        if commit:
            user.save()

        return user


# form anggota (class ModelForm)
class AnggotaForm(forms.ModelForm):

    # field tambahan password
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False),
        required=False,
        label="Password"
    )

    # field nomor telepon dengan validator
    no_telp = forms.CharField(
        label="Nomor Telepon",
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message='Nomor Telepon hanya boleh berisi angka.'
            )
        ]
    )

    # field email dengan validator
    email = forms.CharField(
        label="Email",
        validators=[
            EmailValidator(message="Masukkan alamat email yang valid.")
        ]
    )

    # field umur (integer)
    umur = forms.IntegerField(
        label="Umur",
        min_value=0,
        error_messages={
            "required": "Umur wajib diisi.",
            "invalid": "Umur harus berupa angka bulat (contoh: 15, bukan 15.5).",
            "min_value": "Umur tidak boleh negatif."
        }
    )

    # field pekerjaan dengan validasi huruf
    pekerjaan = forms.CharField(
        label="Pekerjaan",
        validators=[
            RegexValidator(
                regex=r'[a-zA-Z]',
                message='Pekerjaan harus mengandung huruf.'
            )
        ]
    )

    # field alamat
    alamat = forms.CharField(
        label="Alamat",
        validators=[
            RegexValidator(
                regex=r'[a-zA-Z]',
                message='Alamat harus mengandung huruf.'
            )
        ]
    )

    # konfigurasi model
    class Meta:
        model = Anggota
        exclude = ["password_hash"]

        labels = {
            "nomor_anggota": "Nomor Anggota",
            "nama": "Nama Lengkap",
            "nip": "NIP",
            "jenis_kelamin": "Jenis Kelamin",
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

    # method constructor
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # kondisi edit atau tambah
        if self.instance.pk:
            self.fields["password"].required = False
            self.fields["password"].label = "Password Baru"
            self.fields["password"].widget.attrs["placeholder"] = \
                "Masukkan password baru (opsional)"

            # field tidak bisa diubah
            self.fields["nomor_anggota"].disabled = True
        else:
            self.fields["password"].required = True
            self.fields["password"].widget.attrs["placeholder"] = \
                "Masukkan password"

        # loop semua field untuk set pesan error
        for field in self.fields.values():
            if field.required:
                field.error_messages.update({
                    "required": f"{field.label} wajib diisi."
                })

        # placeholder untuk field
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

        # set placeholder
        for name, text in placeholders.items():
            if name in self.fields:
                self.fields[name].widget.attrs.update({
                    "placeholder": text
                })

        # format input tanggal
        self.fields["tanggal_daftar"].input_formats = ["%Y-%m-%d"]
        self.fields["tanggal_nonaktif"].input_formats = ["%Y-%m-%d"]

        if "jenis_kelamin" in self.fields:
            self.fields["jenis_kelamin"].choices = [
                ("", "Pilih Jenis Kelamin"),
                ("Laki-laki", "Laki-laki"),
                ("Perempuan", "Perempuan"),
            ]

    # method validasi global
    def clean(self):
        cleaned_data = super().clean()

        status = cleaned_data.get("status")
        alasan = cleaned_data.get("alasan_nonaktif")
        tanggal = cleaned_data.get("tanggal_nonaktif")

        # validasi jika status nonaktif
        if status and status.lower() == "nonaktif":
            if not alasan:
                self.add_error("alasan_nonaktif", "Alasan tidak aktif wajib diisi.")
            if not tanggal:
                self.add_error("tanggal_nonaktif", "Tanggal tidak aktif wajib diisi.")

        return cleaned_data

    # method validasi no_telp
    def clean_no_telp(self):
        no_telp = self.cleaned_data.get("no_telp")

        if no_telp and not no_telp.isdigit():
            raise forms.ValidationError("Nomor Telepon hanya boleh berisi angka.")

        return no_telp

    # method simpan data
    def save(self, commit=True):
        anggota = super().save(commit=False)  # objek model Anggota

        password = self.cleaned_data.get("password")

        if password:
            anggota.set_password(password)

        if commit:
            anggota.save()

        return anggota