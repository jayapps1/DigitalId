# digital_id/forms.py
from django import forms
from .models import IDRequest
from .models import User, OfficerProfile
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model
from .constants import FIRE_STATION_CHOICES


User = get_user_model()

class OfficerImportForm(forms.ModelForm):
    # Fields from OfficerProfile
    rank = forms.CharField(required=False)
    station = forms.CharField(required=False)

    class Meta:
        model = User
        # Only include the fields you want from User
        fields = ['staffid','service_number', 'firstname', 'lastname', 'gender', 'role', 'region','district']

    def save(self, commit=True):
        # Save User first
        user = super().save(commit=False)
        if not user.password:
            user.set_password('Officer@123')  # Default password
        if commit:
            user.save()

        # Save OfficerProfile linked to this user
        OfficerProfile.objects.update_or_create(
            user=user,
            defaults={
                'rank': self.cleaned_data.get('rank', ''),
                'station': self.cleaned_data.get('station', ''),
            }
        )

        return user



class IDRequestForm(forms.ModelForm):
    class Meta:
        model = IDRequest
        fields = ["request_type"]
        widgets = {
            "request_type": forms.RadioSelect()
        }
        labels = {
            "request_type": "Select Request Type"
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        allowed_types = kwargs.pop("allowed_types", None)
        super().__init__(*args, **kwargs)

        # Dynamically restrict request types
        if allowed_types is not None:
            self.fields["request_type"].choices = [
                choice for choice in self.fields["request_type"].choices
                if choice[0] in allowed_types
            ]

    def clean(self):
        cleaned_data = super().clean()

        if not self.user:
            return cleaned_data

        # Block if pending request exists
        has_pending = IDRequest.objects.filter(
            officer=self.user,
            approval__status="PENDING"
        ).exists()

        if has_pending:
            raise forms.ValidationError(
                "You already have a pending ID request awaiting approval."
            )

        return cleaned_data
    


class AdminOfficerRegistrationForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=True,
        label="Role",
        widget=forms.Select(attrs={"class": "form-select text-uppercase"})
    )

    station = forms.ChoiceField(
        choices=FIRE_STATION_CHOICES,
        required=True,
        label="Station",
        widget=forms.Select(attrs={"class": "form-select text-uppercase"})
    )

    rank = forms.ChoiceField(
        choices=OfficerProfile._meta.get_field("rank").choices,
        required=True,
        label="Rank",
        widget=forms.Select(attrs={"class": "form-select text-uppercase"})
    )

    password = forms.CharField(
        label="Initial Password (optional)",
        widget=forms.PasswordInput(attrs={"placeholder": "Leave blank for default"}),
        required=False
    )
    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm password"}),
        required=False
    )

    is_staff = forms.BooleanField(required=False, label="Staff Status (Can access admin)")
    is_superuser = forms.BooleanField(required=False, label="Superuser Status (Full admin privileges)")

    class Meta:
        model = User
        fields = [
            "staffid",
            "service_number",
            "firstname",
            "lastname",
            "gender",
            "role",
            "region",
            "district",
            "is_staff",
            "is_superuser",
        ]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Bootstrap classes
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-select text-uppercase"})
            else:
                field.widget.attrs.update({"class": "form-control text-uppercase"})

        # Only superusers can see superuser checkbox
        if self.request and not self.request.user.is_superuser:
            self.fields.pop("is_superuser", None)

        # Restrict stations/regions
        if self.request:
            current_user = self.request.user
            if current_user.role == "STATION_ADMIN":
                self.fields["station"].initial = current_user.profile.station
                self.fields["station"].widget.attrs["readonly"] = True
                self.fields["region"].initial = current_user.region
                self.fields["region"].widget.attrs["readonly"] = True
            elif current_user.role == "REGIONAL_ADMIN":
                self.fields["region"].initial = current_user.region
                self.fields["region"].widget.attrs["readonly"] = True
                self.fields["station"].choices = [
                    (code, name) for code, name in FIRE_STATION_CHOICES
                    if current_user.region.lower() in name.lower()
                ]

    # -------------------------
    # Clean methods
    # -------------------------
    def clean_staffid(self):
        return self.cleaned_data.get("staffid", "").upper().strip()

    def clean_station(self):
        station = self.cleaned_data.get("station")
        return station.upper() if station else station

    def clean_region(self):
        region = self.cleaned_data.get("region")
        return region.upper() if region else region

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password or password_confirm:
            if password != password_confirm:
                raise forms.ValidationError("Passwords do not match")

        # Prevent non-superadmins from creating superusers
        if self.request:
            current_user = self.request.user
            if current_user.role in ["STATION_ADMIN", "REGIONAL_ADMIN"]:
                if cleaned_data.get("is_superuser"):
                    raise forms.ValidationError("Only superusers can create other superusers.")

        return cleaned_data

    # -------------------------
    # Save method
    # -------------------------
    def save(self, commit=True):
        with transaction.atomic():
            user = super().save(commit=False)
            user.set_password(self.cleaned_data.get("password") or "Officer@123")

            # Only superusers can set superuser
            if self.request and self.request.user.is_superuser:
                user.is_superuser = self.cleaned_data.get("is_superuser", False)
                user.is_staff = self.cleaned_data.get("is_staff", False)
            else:
                user.is_superuser = False
                # Non-superadmins can only set staff if their role allows
                user.is_staff = self.cleaned_data.get("is_staff", False) if self.request.user.role in ["STATION_ADMIN", "REGIONAL_ADMIN"] else False

            if commit:
                user.save()

            # Save OfficerProfile
            profile, _ = OfficerProfile.objects.get_or_create(user=user)
            profile.station = self.cleaned_data["station"]
            profile.rank = self.cleaned_data["rank"]
            profile.save()

            # Ensure region is saved on user
            user.region = self.cleaned_data["region"]
            if commit:
                user.save(update_fields=["region", "is_superuser", "is_staff"])

        return user
