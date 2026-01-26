from django import forms
from .models import User

class PengurusForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=False,
        help_text="Kosongkan jika tidak ingin mengubah password"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'role', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user