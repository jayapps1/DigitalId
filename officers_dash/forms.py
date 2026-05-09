from django import forms
from django.contrib.auth import get_user_model
from digital_id.models import OfficerProfile, User
from digital_id.constants import FIRE_STATION_CHOICES
from django.db import transaction

User = get_user_model()


# -------------------------
# Officer Profile Form (internal, admin use)
# -------------------------
class OfficerProfileForm(forms.ModelForm):
    """
    Form used to edit OfficerProfile fields.
    Admins may edit rank only, station is searchable.
    """
    station = forms.ChoiceField(
        choices=[("", "")] + list(FIRE_STATION_CHOICES),
        required=False,
        label="Station",
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",
            "data-placeholder": "Type or select fire station",
        }),
    )

    class Meta:
        model = OfficerProfile
        fields = ["rank", "station"]
        widgets = {
            "rank": forms.Select(attrs={
                "class": "form-select text-uppercase select2",
                "data-placeholder": "Select rank",
            }),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control text-uppercase")


ADMIN_ROLE_CHOICES = [role for role in User.ROLE_CHOICES if role[0] != "OFFICER"]


# -------------------------
# Officer User Update Form
# -------------------------
class OfficerUserUpdateForm(forms.ModelForm):
    photo = forms.ImageField(required=False, label="Profile Picture")

    rank = forms.ChoiceField(
        choices=[("", "")] + list(OfficerProfile._meta.get_field("rank").choices),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",
            "data-placeholder": "Select rank",
        }),
    )

    blood_group = forms.ChoiceField(
        choices=[("", "")] + list(OfficerProfile._meta.get_field("blood_group").choices),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",
            "data-placeholder": "Select blood group",
        }),
    )

    station = forms.ChoiceField(
        choices=[("", "")] + list(FIRE_STATION_CHOICES),
        required=False,
        label="Station",
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",
            "data-placeholder": "Type or select fire station",
        }),
    )

    region = forms.ChoiceField(
        choices=[("", "")] + list(User.REGION_CHOICES),
        required=False,
        label="Region",
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",
            "data-placeholder": "Select region",
        }),
    )

    district = forms.CharField(
        required=False,
        label="District",
        widget=forms.TextInput(attrs={
            "class": "form-control text-uppercase",
            "placeholder": "Enter district"
        }),
    )

    class Meta:
        model = User
        fields = [
            "firstname",
            "lastname",
            "email",
            "phone",
            "emergency_contact",
            "gender",
            "ghcard",
            "service_number",
            "region",
            "district",
        ]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.profile_instance = kwargs.pop("profile_instance", None)
        super().__init__(*args, **kwargs)

        if not self.profile_instance:
            raise ValueError("OfficerUserUpdateForm requires profile_instance")

        # Pre-fill OfficerProfile fields
        self.fields["rank"].initial = self.profile_instance.rank
        self.fields["blood_group"].initial = self.profile_instance.blood_group
        self.fields["station"].initial = self.profile_instance.station
        self.fields["photo"].initial = self.profile_instance.photo

        # Pre-fill User fields
        self.fields["region"].initial = getattr(self.instance, "region", "")
        self.fields["district"].initial = getattr(self.instance, "district", "")

        # Apply bootstrap class to all fields
        for field_name, field in self.fields.items():
            existing_class = field.widget.attrs.get("class", "")
            if "select2" not in existing_class and field_name not in ["rank", "blood_group", "station", "region"]:
                field.widget.attrs["class"] = f"{existing_class} form-control text-uppercase".strip()

    def save(self, commit=True):
        user = super().save(commit=False)

        profile = self.profile_instance
        profile.rank = self.cleaned_data.get("rank")
        profile.blood_group = self.cleaned_data.get("blood_group")
        profile.station = self.cleaned_data.get("station")

        if self.cleaned_data.get("photo"):
            profile.photo = self.cleaned_data["photo"]

        user.region = self.cleaned_data.get("region", user.region)
        user.district = self.cleaned_data.get("district", getattr(user, "district", ""))

        if commit:
            profile.save()
            user.save()

        return user


# -------------------------
# Admin Officer Update Form
# -------------------------
class AdminOfficerUpdateForm(OfficerUserUpdateForm):
    admin_roles = forms.ChoiceField(
        required=False,
        label="Administrative Role",
        widget=forms.Select(attrs={"class": "form-select text-uppercase"})
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Only superadmins can see role selector
        if not (self.request and self.request.user.is_superuser):
            self.fields.pop("admin_roles", None)
            return

        # ✅ USE FULL ROLE LIST (INCLUDING OFFICER)
        self.fields["admin_roles"].choices = User.ROLE_CHOICES

        # ✅ ALWAYS PREFILL CURRENT ROLE
        self.fields["admin_roles"].initial = self.instance.role

    def clean(self):
        cleaned = super().clean()

        if not (self.request and self.request.user.is_superuser):
            return cleaned

        selected_role = cleaned.get("admin_roles")
        acting_user = self.request.user
        instance_user = self.instance

        # Prevent self-demotion
        if (
            acting_user == instance_user
            and acting_user.is_superuser
            and selected_role != "SUPERADMIN"
        ):
            raise forms.ValidationError(
                "You cannot remove your own superadmin privileges."
            )

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.request and self.request.user.is_superuser:
            role = self.cleaned_data.get("admin_roles")

            if role:
                user.role = role
                user.is_staff = role in [
                    "SUPERADMIN",
                    "REGIONAL_ADMIN",
                    "STATION_ADMIN",
                ]
                user.is_superuser = role == "SUPERADMIN"

        if commit:
            self.profile_instance.save()
            user.save()

        return user

# -------------------------
# Officer Self Update Form
# -------------------------
class OfficerSelfUpdateForm(forms.ModelForm):
    photo = forms.ImageField(required=False, label="Profile Picture")

    blood_group = forms.ChoiceField(
        choices=[("", "")] + list(OfficerProfile._meta.get_field("blood_group").choices),
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",
            "data-placeholder": "Select blood group",
        }),
    )

    class Meta:
        model = User
        fields = ["email", "phone", "emergency_contact", "ghcard"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.profile_instance = kwargs.pop("profile_instance", None)
        super().__init__(*args, **kwargs)
        if not self.profile_instance:
            raise ValueError("OfficerSelfUpdateForm requires profile_instance")

        self.fields["photo"].initial = self.profile_instance.photo
        self.fields["blood_group"].initial = self.profile_instance.blood_group

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control text-uppercase")

    def save(self, commit=True):
        user = super().save(commit=False)
        self.profile_instance.blood_group = self.cleaned_data.get("blood_group")
        if self.cleaned_data.get("photo"):
            self.profile_instance.photo = self.cleaned_data["photo"]

        if commit:
            self.profile_instance.save()
            user.save()

        return user
