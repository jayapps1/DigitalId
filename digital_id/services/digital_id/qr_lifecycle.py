from datetime import timedelta
from django.utils import timezone
from digital_id.models import OfficerProfile
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)

def activate_qr(profile, days=None, approved_by=None):
    """
    Activates an officer QR without regenerating token.
    Overrides expiry to 5 years by default.
    Can still accept 'days' if you explicitly want a different duration.
    """
    now = timezone.now()

    profile.is_active_qr = True
    profile.date_approved = now

    # Override expiry: 5 years from now by default
    if days is None:
        profile.qr_expiry_date = now + relativedelta(years=5)
    else:
        profile.qr_expiry_date = now + timedelta(days=days)

    profile.save(update_fields=[
        "is_active_qr",
        "date_approved",
        "qr_expiry_date"
    ])
    logger.info(
        f"QR activated for {profile.user.staffid}, expires on {profile.qr_expiry_date}"
    )


def override_existing_qr_expiry():
    """
    For production: updates all existing active QR codes to have 5-year expiry
    from date_approved if they are currently less than 5 years.
    """
    now = timezone.now()
    profiles = OfficerProfile.objects.filter(is_active_qr=True)

    for profile in profiles:
        if not profile.qr_expiry_date or profile.qr_expiry_date < profile.date_approved + relativedelta(years=5):
            profile.qr_expiry_date = profile.date_approved + relativedelta(years=5)
            profile.save(update_fields=["qr_expiry_date"])
            logger.info(f"Updated existing QR expiry for {profile.user.staffid} to {profile.qr_expiry_date}")

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
