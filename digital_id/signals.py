# digital_id/signals.py
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from digital_id.models import OfficerProfile, IDRequestApproval
from digital_id.qr_service import send_qr_link
import logging

logger = logging.getLogger(__name__)
User = settings.AUTH_USER_MODEL


# -------------------------
# Create OfficerProfile automatically (SINGLE SOURCE OF TRUTH)
# -------------------------
@receiver(post_save, sender=User)
def ensure_officer_profile(sender, instance, created, **kwargs):
    """
    Ensures exactly ONE OfficerProfile per User.
    Safe for:
    - Admin registration
    - Excel import
    - User updates
    """
    if created:
        OfficerProfile.objects.get_or_create(user=instance)


# -------------------------
# Reset lost_request_pending flag when ID request is processed
# -------------------------
@receiver(post_save, sender=IDRequestApproval)
def reset_pending_flag(sender, instance, **kwargs):
    if instance.status in ["APPROVED", "REJECTED"]:
        profile = instance.id_request.officer.profile

        if profile.lost_request_pending:
            def reset_flag():
                profile.lost_request_pending = False
                profile.save(update_fields=["lost_request_pending"])

            transaction.on_commit(reset_flag)


# -------------------------
# Send QR SMS only after admin approves ID request
# -------------------------
@receiver(post_save, sender=IDRequestApproval)
def send_qr_sms_on_approval(sender, instance, **kwargs):
    if instance.status == "APPROVED":
        profile = instance.id_request.officer.profile
        user = profile.user

        if user.preferred_qr_method == "sms":
            def send_qr_sms():
                result = send_qr_link(profile)
                if result.get("success"):
                    logger.info(f"QR SMS sent to officer {user.staffid}")
                else:
                    logger.error(
                        f"Failed to send QR SMS to {user.staffid}: {result.get('error')}"
                    )

            transaction.on_commit(send_qr_sms)
