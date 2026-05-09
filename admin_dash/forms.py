# admin_dash/forms.py
from django import forms

from django.contrib.auth import get_user_model

User = get_user_model()

class SuperUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["staffid", "email"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user


class OfficerRoleAssignForm(forms.Form):
    officer = forms.ModelChoiceField(queryset=User.objects.none(), label="Officer")
    role = forms.ChoiceField(choices=[], label="Assign Role")

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Determine assignable officers based on current user's role
        if not self.request:
            return

        user = self.request.user

        if user.role == "SUPERADMIN":
            self.fields["officer"].queryset = User.objects.exclude(staffid=user.staffid)
            self.fields["role"].choices = User.ROLE_CHOICES
        elif user.role == "REGIONAL_ADMIN":
            # Only officers in the same region
            self.fields["officer"].queryset = User.objects.filter(region=user.region).exclude(staffid=user.staffid)
            # Limit roles: cannot assign SUPERADMIN or other regional admins outside the same region
            self.fields["role"].choices = [r for r in User.ROLE_CHOICES if r[0] in ["OFFICER", "STATION_ADMIN"]]
        else:
            # Other roles cannot assign
            self.fields["officer"].queryset = User.objects.none()
            self.fields["role"].choices = []

    def clean(self):
        cleaned = super().clean()
        officer = cleaned.get("officer")
        role = cleaned.get("role")

        if not self.request or not officer or not role:
            return cleaned

        user = self.request.user

        # Prevent self-demotion
        if user == officer and officer.is_superuser and role != "SUPERADMIN":
            raise forms.ValidationError("You cannot remove your own superadmin privileges.")

        # Regional admin cannot assign outside region
        if user.role == "REGIONAL_ADMIN" and officer.region != user.region:
            raise forms.ValidationError("You cannot assign roles to officers outside your region.")

        return cleaned