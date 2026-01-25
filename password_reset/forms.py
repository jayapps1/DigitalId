# password_reset/forms.py
from django import forms

class PasswordResetRequestForm(forms.Form):
    service_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your Service Number"
        })
    )
    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your Registered Phone Number"
        })
    )

class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.HiddenInput()  # hidden input now receives combined value
    )

    def clean_otp(self):
        otp = self.cleaned_data.get("otp", "")
        if not otp.isdigit():
            raise forms.ValidationError("OTP must contain only digits.")
        if len(otp) != 6:
            raise forms.ValidationError("OTP must be 6 digits.")
        return otp

class SetPasswordForm(forms.Form):
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "New Password"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm Password"})
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match")
        return cleaned
