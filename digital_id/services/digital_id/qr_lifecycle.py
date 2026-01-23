from datetime import timedelta
from django.utils import timezone
from digital_id.models import OfficerProfile

def activate_qr(profile, days=365, approved_by=None):
    """
    Activates an officer QR without regenerating token.
    Sets expiry according to the specified number of days.
    """
    profile.is_active_qr = True
    profile.qr_expiry_date = timezone.now() + timedelta(days=days)
    profile.date_approved = timezone.now()
    profile.save(update_fields=[
        "is_active_qr",
        "qr_expiry_date",
        "date_approved"
    ])


def deactivate_qr(profile):
    """
    Deactivates QR (lost, suspended, revoked).
    """
    profile.is_active_qr = False
    profile.save(update_fields=["is_active_qr"])


def deactivate_expired_qrs(profiles=None):
    """
    Deactivates all QR codes that have passed their expiry date.
    If `profiles` is provided, only checks those; otherwise checks all officers.
    """
    if profiles is None:
        profiles = OfficerProfile.objects.all()

    now = timezone.now()
    expired_profiles = profiles.filter(is_active_qr=True, qr_expiry_date__lt=now)

    for profile in expired_profiles:
        profile.is_active_qr = False
        profile.save(update_fields=["is_active_qr"])
