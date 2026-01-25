from django import forms
from django.contrib.auth import get_user_model
from digital_id.models import OfficerProfile
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
        choices=FIRE_STATION_CHOICES,
        required=False,
        label="Station",
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",  # select2 enables search
        }),
    )

    class Meta:
        model = OfficerProfile
        fields = ["rank", "station"]
        widgets = {
            "rank": forms.Select(attrs={"class": "form-select text-uppercase"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control text-uppercase")



class OfficerUserUpdateForm(forms.ModelForm):
    photo = forms.ImageField(required=False, label="Profile Picture")

    # Profile fields
    rank = forms.ChoiceField(
        choices=OfficerProfile._meta.get_field("rank").choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select text-uppercase select2"}),
    )
    blood_group = forms.ChoiceField(
        choices=OfficerProfile._meta.get_field("blood_group").choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select text-uppercase select2"}),
    )
    station = forms.ChoiceField(
        choices=FIRE_STATION_CHOICES,
        required=False,
        label="Station",
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",
        }),
    )

    # User fields
    region = forms.ChoiceField(
        choices=User.REGION_CHOICES,
        required=False,
        label="Region",
        widget=forms.Select(attrs={"class": "form-select text-uppercase select2"}),
    )

    class Meta:
        model = User
        fields = [
            "firstname",
            "lastname",
            "email",
            "phone",
            "gender",
            "ghcard",
            "service_number",
            "region",
        ]

    def __init__(self, *args, **kwargs):
        self.profile_instance = kwargs.pop("profile_instance", None)
        super().__init__(*args, **kwargs)
        if not self.profile_instance:
            raise ValueError("OfficerUserUpdateForm requires profile_instance")

        # Set initial values for profile fields
        self.fields["rank"].initial = self.profile_instance.rank
        self.fields["blood_group"].initial = self.profile_instance.blood_group
        self.fields["station"].initial = self.profile_instance.station
        self.fields["photo"].initial = self.profile_instance.photo
        self.fields["region"].initial = self.instance.region

        # Add default classes
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control text-uppercase")

    def save(self, commit=True):
        user = super().save(commit=False)

        # Save profile
        self.profile_instance.rank = self.cleaned_data.get("rank")
        self.profile_instance.blood_group = self.cleaned_data.get("blood_group")
        self.profile_instance.station = self.cleaned_data.get("station")
        if self.cleaned_data.get("photo"):
            self.profile_instance.photo = self.cleaned_data["photo"]

        # Save user fields
        user.region = self.cleaned_data.get("region", user.region)

        if commit:
            self.profile_instance.save()
            user.save()
        return user
    
    
class OfficerSelfUpdateForm(forms.ModelForm):
    photo = forms.ImageField(required=False, label="Profile Picture")

    blood_group = forms.ChoiceField(
        choices=OfficerProfile._meta.get_field("blood_group").choices,
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase",
            "data-live-search": "true"
        }),
    )

    region = forms.ChoiceField(
        choices=User.REGION_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase",
            "data-live-search": "true"
        }),
    )

    station = forms.ChoiceField(
        choices=FIRE_STATION_CHOICES,
        required=False,
        label="Station",
        widget=forms.Select(attrs={
            "class": "form-select text-uppercase select2",  # <-- select2 class
            "style": "width:100%",  # optional for full width
        }),
    )

    class Meta:
        model = User
        fields = ["email", "phone", "ghcard", "region", "station"]

    def __init__(self, *args, **kwargs):
        self.profile_instance = kwargs.pop("profile_instance", None)
        super().__init__(*args, **kwargs)
        if not self.profile_instance:
            raise ValueError("OfficerSelfUpdateForm requires profile_instance")

        # Populate profile-backed fields
        self.fields["photo"].initial = self.profile_instance.photo
        self.fields["blood_group"].initial = self.profile_instance.blood_group
        self.fields["region"].initial = self.instance.region
        self.fields["station"].initial = self.profile_instance.station

    def save(self, commit=True):
        user = super().save(commit=False)

        # Save profile fields
        self.profile_instance.blood_group = self.cleaned_data.get("blood_group")
        self.profile_instance.station = self.cleaned_data.get("station")
        if self.cleaned_data.get("photo"):
            self.profile_instance.photo = self.cleaned_data["photo"]

        # Save user fields
        user.region = self.cleaned_data.get("region", user.region)

        if commit:
            self.profile_instance.save()
            user.save()
        return user
