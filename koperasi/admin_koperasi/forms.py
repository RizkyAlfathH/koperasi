from django import forms
from .models import User

class PengurusForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        label="Password"
    )

    class Meta:
        model = User
        fields = ['username', 'role', 'password']

    def clean_role(self):
        role = self.cleaned_data['role']
        if role == 'admin':
            raise forms.ValidationError("Tidak boleh membuat admin.")
        return role

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')

        if pwd:
            user.set_password(pwd)

        if commit:
            user.save()
        return user
