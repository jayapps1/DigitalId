from django.db import models, IntegrityError
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.conf import settings
import os, qrcode, uuid
from io import BytesIO
from django.core.files.base import ContentFile
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from PIL import Image, ImageDraw, ImageFont
import requests
from django.core.mail import send_mail
import logging
from digital_id.qr_service import send_qr_link  # <--- new import
from django.core.exceptions import ValidationError
from PIL import Image, ImageDraw, ImageFont
from django.urls import reverse
from django.contrib.auth import get_user_model



# -------------------------
# USER MANAGER
# -------------------------
class UserManager(BaseUserManager):
    def create_user(self, staffid, password=None, **extra_fields):
        if not staffid:
            raise ValueError("Staff ID is required")
        staffid = staffid.upper().strip()
        user = self.model(staffid=staffid, **extra_fields)
        user.set_password(password or "Officer@123")
        user.must_change_password = extra_fields.get("role", "OFFICER") == "OFFICER"
        user.save(using=self._db)
        return user

    def create_superuser(self, staffid, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "SUPERADMIN")
        extra_fields.setdefault("must_change_password", False)
        return self.create_user(staffid, password, **extra_fields)


# -------------------------
# USER MODEL
# -------------------------
class User(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = (("M", "Male"), ("F", "Female"))
    ROLE_CHOICES = (
    ("OFFICER", "Officer"),
    ("STATION_ADMIN", "Station Admin"),
    ("REGIONAL_ADMIN", "Regional Admin"),
    ("SUPERADMIN", "System Super Admin"),
)

    REGION_CHOICES = (
    ("GREATER_ACC", "Greater Accra"),
    ("ASHANTI", "Ashanti"),
    ("WESTERN", "Western"),
    ("EASTERN", "Eastern"),
    ("NORTHERN", "Northern"),
    ("UPPER_EAST", "Upper East"),
    ("UPPER_WEST", "Upper West"),
    ("VOLTA", "Volta"),
    ("BONO", "Bono"),
    ("BONO_EAST", "Bono East"),
    ("AHAFO", "Ahafo"),
    ("Oti", "Oti"),
    ("SAVANNAH", "Savannah"),
    ("NORTH_EAST", "North East"),
    ("WESTERN_NORTH", "Western North"),
    ("CENTRAL", "Central"),
)


    staffid = models.CharField(
        max_length=20,
        primary_key=True
    )

    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    service_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    ghcard = models.CharField(
        max_length=25,
        unique=True,
        blank=True,
        null=True
    )

    region = models.CharField( max_length=20, choices=REGION_CHOICES, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)

    phone = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True
    )

    # In your User model
    emergency_contact = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        help_text="Emergency contact number shown on ID card"
    )



    email = models.EmailField(
        max_length=254,
        unique=True,
        blank=True,
        null=True
    )

    QR_METHOD_CHOICES = (
        ("email", "Email"),
        ("sms", "SMS"),
    )
    preferred_qr_method = models.CharField(
        max_length=10,
        choices=QR_METHOD_CHOICES,
        default="email"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="OFFICER",
        db_index=True
    )

    must_change_password = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "staffid"
    REQUIRED_FIELDS = ["firstname", "lastname", "gender"]

    # -------------------------
    # STRING
    # -------------------------
    def __str__(self):
        return f"{self.staffid} - {self.firstname} {self.lastname}"

     # -------------------------
    # HELPER: safe string normalization
    # -------------------------
    @staticmethod
    def _safe_str(value, upper=False):
        if value is None:
            return ""
        value = str(value).strip()
        if upper:
            value = value.upper()
        return value

      # -------------------------
    # ROLE HELPERS
    # -------------------------
    @property
    def is_officer(self):
        return self.role == "OFFICER"

    def get_full_name(self):
        return f"{self.firstname} {self.lastname}"

    @property
    def profile_completed(self):
        # Required user fields
        required_user_fields = [
            "service_number",
            "ghcard",
            "region",
            "district",
            "emergency_contact",
            "email",
        ]
        # Required profile fields
        required_profile_fields = ["photo", "rank", "station"]

        # Get profile
        profile = getattr(self, "profile", None)
        if not profile:
            return False

        # Check required user fields
        for field in required_user_fields:
            if not getattr(self, field, None):
                return False

        # Check required profile fields
        for field in required_profile_fields:
            if not getattr(profile, field, None):
                return False

        return True

        # -------------------------
    # MODEL VALIDATION (FRIENDLY ERRORS)
    # -------------------------
    def clean(self):

        unique_fields = {
            "service_number": "Service number already exists.",
            "phone": "Phone number already exists.",
            "emergency_contact": "Emergency Phone number already exists.",
            "ghcard": "Ghana Card number already exists.",
            "email": "Email address already exists.",
        }

        # Check uniqueness for each field
        for field, message in unique_fields.items():
            value = getattr(self, field)
            if value:
                qs = User.objects.filter(**{field: value})
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
                if qs.exists():
                    raise ValidationError({field: message})





    # -------------------------
    # SAVE (NORMALIZATION + SAFETY)
    # -------------------------
    def save(self, *args, **kwargs):

        # -------------------------
        # SAFETY: ensure password exists before validation
        # -------------------------
        if not self.password:
            self.set_unusable_password()

        # -------------------------
        # Normalize staff ID
        # -------------------------
        if self.staffid is not None:
            self.staffid = self._safe_str(self.staffid, upper=True)

        # -------------------------
        # Normalize Ghana Card → GHA-XXXXXXXXX-X
        # -------------------------
        if self.ghcard:
            clean_gh = (
                self._safe_str(self.ghcard, upper=True)
                .replace("GHA-", "")
                .replace("-", "")
            )
            if len(clean_gh) >= 10:
                self.ghcard = f"GHA-{clean_gh[:-1]}-{clean_gh[-1]}"
            else:
                self.ghcard = f"GHA-{clean_gh}"


        # -------------------------
        # Normalize phone → +233XXXXXXXXX
        # -------------------------
        if self.phone:
            phone = self._safe_str(self.phone)
            if phone.startswith("0"):
                phone = "+233" + phone[1:]
            elif phone.startswith("233"):
                phone = "+233" + phone[3:]
            elif not phone.startswith("+233"):
                phone = "+233" + phone
            self.phone = phone

        if self.emergency_contact:
            emergency_contact = self._safe_str(self.emergency_contact)
            if emergency_contact.startswith("0"):
                emergency_contact = "+233" + emergency_contact[1:]
            elif emergency_contact.startswith("233"):
                emergency_contact = "+233" + emergency_contact[3:]
            elif not emergency_contact.startswith("+233"):
                emergency_contact = "+233" + emergency_contact
            self.emergency_contact = emergency_contact


        # -------------------------
        # Normalize and validate service number
        # -------------------------
        if self.service_number:
            import re
            service_number = self._safe_str(self.service_number, upper=True)

            pattern = r'^(GF\d{5,6}[A-Z]|\d{7,8}[A-Z])$'

            if not re.fullmatch(pattern, service_number):
                raise ValidationError({
                    "service_number": (
                        "Service number must be:\n"
                        "- 7–8 digits followed by a letter (e.g., 2025500J)\n"
                        "- OR start with GF, followed by 5–6 digits and a letter (e.g., GF200058D)"
                    )
                })


        # -------------------------
        # Run validations (SAFE)
        # -------------------------
        self.full_clean()

        # -------------------------
        # Final DB safety net
        # -------------------------
        try:
            super().save(*args, **kwargs)
        except IntegrityError:
            raise ValidationError(
                "Duplicate data detected. One or more unique fields already exist."
            )




from .constants import FIRE_STATION_CHOICES  # <-- import the tuple

import time




from django.db import models

from django.utils import timezone



class OfficerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    sms_sent = models.BooleanField(default=False)
    photo = models.ImageField(upload_to="officers/photos/", blank=True, null=True)

    rank = models.CharField(
        max_length=5,
        choices=(("NCO", "Non-Commissioned Officer"), ("CO", "Commissioned Officer")),
        default="NCO"
    )

    BLOOD_GROUP_CHOICES = (
        ("A Positive", "A Positive"),
        ("A Negetive", "A Negetive"),
        ("B Positive", "B Positive"),
        ("B Negetive", "B Negetive"),
        ("AB Positive", "AB Positive"),
        ("AB Negetive", "AB Negetive"),
        ("O Positive", "O Positive"),
        ("O Negetive", "O Negetive"),
    )

    blood_group = models.CharField(max_length=12, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
    station = models.CharField(max_length=255, choices=FIRE_STATION_CHOICES, blank=True, null=True)

    # Leave
    LEAVE_CHOICES = (
        ("AT_POST", "At Post"),
        ("ON_LEAVE", "On Leave"),
        ("STUDY_LEAVE", "Study Leave"),
        ("MATERNITY_LEAVE", "Maternity Leave"),
        ("SICK_LEAVE", "Sick Leave"),
        ("TERMINAL_LEAVE", "Terminal Leave"),
    )

    leave_type = models.CharField(max_length=20, choices=LEAVE_CHOICES, default="AT_POST")
    leave_start = models.DateField(blank=True, null=True)
    leave_end = models.DateField(blank=True, null=True)
    called_off = models.BooleanField(default=False)

    # Identity
    qr_token = models.CharField(max_length=12, unique=True, editable=False)

    qr_image = models.ImageField(upload_to="officers/qrcodes/", blank=True, null=True)
    front_qr_image = models.ImageField(upload_to="officers/front_qrcodes/", blank=True, null=True)
    service_id_image = models.ImageField(upload_to="officers/service_ids/", blank=True, null=True)

    is_active_qr = models.BooleanField(default=False)
    qr_expiry_date = models.DateTimeField(null=True, blank=True)
    date_approved = models.DateTimeField(null=True, blank=True)

    lost_request_pending = models.BooleanField(default=False)
    qr_revoked = models.BooleanField(default=False)

    # =========================
    # SAVE (FIXED)
    # =========================
    def save(self, *args, **kwargs):
        today = timezone.localdate()

        # Leave logic
        if self.called_off:
            self.leave_type = "AT_POST"
        elif self.leave_start and self.leave_end and self.leave_start <= today <= self.leave_end:
            self.leave_type = self.leave_type or "ON_LEAVE"
        else:
            self.leave_type = "AT_POST"

        # Token
        if not self.qr_token:
            self.qr_token = uuid.uuid4().hex[:12].upper()

        if not self.user:
            raise ValidationError("OfficerProfile must be linked to a User.")

        creating = self.pk is None

        # FIRST SAVE
        super().save(*args, **kwargs)

        # =========================
        # SYNC NFC CARD
        # =========================
        from nfc_cards.models import NFCCard

        card, _ = NFCCard.objects.get_or_create(profile=self)

        if card.qr_token != self.qr_token:
            card.qr_token = self.qr_token
            card.save()

        # =========================
        # GENERATE ASSETS (SAFE)
        # =========================
        if creating or not self.qr_image or not self.front_qr_image:
            self._generate_assets()

            # FINAL SAVE (commit images)
            super().save()

    # =========================
    # QR VALIDITY
    # =========================
    def is_qr_valid(self):
        if not self.is_active_qr:
            return False
        if self.qr_revoked:
            return False
        if self.lost_request_pending:
            return False
        if self.qr_expiry_date and timezone.now() > self.qr_expiry_date:
            return False
        return True

    # =========================
    # GENERATE ALL ASSETS
    # =========================
    def _generate_assets(self):
        self._generate_qr_image()        # BACK → verify
        self._generate_front_qr_image()  # FRONT → vCard
        self._generate_service_id_image()

    # =========================
    # FRONT QR (FIXED)
    # =========================
    def _generate_front_qr_image(self):
        nfc_path = reverse("nfc_cards:nfc_vcard", args=[self.qr_token])
        nfc_url = f"{settings.SITE_URL}{nfc_path}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=3,
            border=2,
        )
        qr.add_data(nfc_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="PNG")

        self.front_qr_image.save(
            f"front_qr_{self.user.staffid}.png",
            ContentFile(buffer.getvalue()),
            save=False,
        )

    # =========================
    # BACK QR (VERIFY)
    # =========================
    def _generate_qr_image(self):
        verify_path = reverse("id_card:verify", args=[self.qr_token])
        verify_url = f"{settings.SITE_URL}{verify_path}"

        qr = qrcode.QRCode(
            version=4,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8,
            border=1,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        buffer = BytesIO()
        img.save(buffer, format="PNG")

        self.qr_image.save(
            f"qr_{self.user.staffid}.png",
            ContentFile(buffer.getvalue()),
            save=False,
        )

    # =========================
    # SERVICE ID
    # =========================
    def _generate_service_id_image(self):
        template_path = os.path.join(
            settings.BASE_DIR,
            "digital_id",
            "static",
            "digital_id",
            "gnfs_template.png"
        )

        card = Image.open(template_path).convert("RGBA")
        card_w, card_h = card.size

        if self.photo and os.path.exists(self.photo.path):
            photo = Image.open(self.photo.path).convert("RGBA")
            photo = photo.resize((80, 90))
            card.paste(photo, ((card_w - 80) // 2, (card_h // 2) - 60), photo)

        buffer = BytesIO()
        card.save(buffer, format="PNG")

        filename = f"service_id_{self.user.staffid}_{int(time.time())}.png"

        self.service_id_image.save(
            filename,
            ContentFile(buffer.getvalue()),
            save=False,
        )

# -------------------------
# NOTIFICATIONS
# -------------------------
class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.staffid} - {self.title}"





class ContactMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # system-controlled snapshots
    staffid = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    station = models.CharField(max_length=150)
    role = models.CharField(max_length=50, default="OFFICER")

    # user-entered
    subject = models.CharField(max_length=150, default="General Inquiry")
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    # NEW: image upload
    image = models.ImageField(upload_to='contact_messages/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staffid} | {self.role} | {self.subject}"



# -------------------------
# ID REQUEST (Officer)
# -------------------------
class IDRequest(models.Model):
    REQUEST_CHOICES = (
        ("NEW", "New ID Request"),
        ("LOST", "Lost QR"),
        ("EXPIRED", "Expired ID Renewal")
    )
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="id_requests"
    )
    request_type = models.CharField(max_length=20, choices=REQUEST_CHOICES)
    date_requested = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.officer.staffid} - {self.request_type} - {self.date_requested.date()}"

    @property
    def is_paid(self):
        """Returns True if this request has a successful linked payment"""
        # Uses the OneToOne relation from Payment
        return hasattr(self, "payment") and self.payment.status == "SUCCESS"


# -------------------------
# ADMIN APPROVAL
# -------------------------
class IDRequestApproval(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    id_request = models.OneToOneField(
        "IDRequest",
        on_delete=models.CASCADE,
        related_name="approval"
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_requests"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    date_processed = models.DateTimeField(null=True, blank=True)

    def clean(self):
        """
        Hard rule:
        Approval cannot move out of PENDING unless payment is SUCCESS
        """
        payment = getattr(self.id_request, "payment", None)
        if self.status in ["APPROVED", "REJECTED"]:
            if not payment or payment.status != "SUCCESS":
                raise ValidationError(
                    "This request cannot be processed because payment is not completed."
                )

        if self.status == "APPROVED":
            if not self.approved_by or not (
                self.approved_by.is_staff or self.approved_by.is_superuser
            ):
                raise PermissionDenied(
                    "Only staff or superusers can approve ID requests."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id_request} - {self.status}"


# -------------------------
# QR SCAN LOG
# -------------------------
class QRScanLog(models.Model):
    profile = models.ForeignKey(OfficerProfile, on_delete=models.CASCADE, related_name="scan_logs")
    scanned_at = models.DateTimeField(auto_now_add=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        ordering = ["-scanned_at"]

    def __str__(self):
        return f"{self.profile.user.staffid} scanned at {self.scanned_at}"
