from django import forms
from django.contrib.auth import get_user_model
from digital_id.models import OfficerProfile

User = get_user_model()


# -------------------------
# Officer Profile Form (internal, admin use)
# -------------------------
class OfficerProfileForm(forms.ModelForm):
    """
    Internal form used to edit OfficerProfile fields.
    Admins may edit rank only.
    """

    class Meta:
        model = OfficerProfile
        fields = ["rank"]
        widgets = {
            "rank": forms.Select(attrs={
                "class": "form-select text-uppercase"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class", "form-control text-uppercase"
            )





class OfficerUserUpdateForm(forms.ModelForm):
    photo = forms.ImageField(required=False, label="Profile Picture")

    region = forms.CharField(
        max_length=100,
        required=False,
        label="Region",
        widget=forms.TextInput(attrs={"class": "form-control text-uppercase"}),
    )

    rank = forms.ChoiceField(
        choices=OfficerProfile._meta.get_field("rank").choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select text-uppercase"}),
    )

    blood_group = forms.ChoiceField(
        choices=OfficerProfile._meta.get_field("blood_group").choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select text-uppercase"}),
    )

    station = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control text-uppercase"}),
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
        if self.profile_instance is None:
            raise ValueError("OfficerUserUpdateForm requires profile_instance")

        # Set default classes
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control text-uppercase")

        # Populate profile-backed fields
        self.fields["rank"].initial = self.profile_instance.rank
        self.fields["station"].initial = self.profile_instance.station
        self.fields["photo"].initial = self.profile_instance.photo
        self.fields["blood_group"].initial = self.profile_instance.blood_group
        self.fields["region"].initial = self.instance.region

    def save(self, commit=True):
        user = super().save(commit=False)

        # Save profile fields
        self.profile_instance.rank = self.cleaned_data.get("rank")
        self.profile_instance.station = self.cleaned_data.get("station")
        self.profile_instance.blood_group = self.cleaned_data.get("blood_group")
        if self.cleaned_data.get("photo"):
            self.profile_instance.photo = self.cleaned_data["photo"]

        # Save User fields
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
        widget=forms.Select(attrs={"class": "form-select text-uppercase"}),
    )

    region = forms.CharField(
        max_length=100,
        required=False,
        label="Region",
        widget=forms.TextInput(attrs={"class": "form-control text-uppercase"}),
    )

    class Meta:
        model = User
        fields = ["email", "phone", "ghcard", "region"]

    def __init__(self, *args, **kwargs):
        self.profile_instance = kwargs.pop("profile_instance", None)
        super().__init__(*args, **kwargs)
        if self.profile_instance is None:
            raise ValueError("OfficerSelfUpdateForm requires profile_instance")

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control text-uppercase")

        self.fields["photo"].initial = self.profile_instance.photo
        self.fields["blood_group"].initial = self.profile_instance.blood_group
        self.fields["region"].initial = self.instance.region

    def save(self, commit=True):
        user = super().save(commit=False)

        self.profile_instance.blood_group = self.cleaned_data.get("blood_group")
        if self.cleaned_data.get("photo"):
            self.profile_instance.photo = self.cleaned_data["photo"]

        user.region = self.cleaned_data.get("region", user.region)

        if commit:
            self.profile_instance.save()
            user.save()
        return user
