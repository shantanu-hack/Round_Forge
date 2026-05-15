from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm

from apps.authentication.models import User


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(max_length=180)
    email = forms.EmailField()
    target_role = forms.CharField(max_length=140, required=False)

    class Meta:
        model = User
        fields = ["full_name", "email", "target_role", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.username = user.email
        user.full_name = self.cleaned_data["full_name"]
        user.target_role = self.cleaned_data.get("target_role", "")
        if commit:
            user.save()
        return user


class EmailLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").lower()
        password = cleaned.get("password")
        if email and password:
            self.user = authenticate(username=email, password=password)
            if self.user is None:
                raise forms.ValidationError("Invalid email or password.")
        return cleaned
