from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from digital_id.models import Notification
from datetime import timedelta
import uuid
from digital_id.qr_service import send_qr_link


@transaction.atomic
def approve_id_request(approval, approved_by, send_sms_flag=True):
    """
    Core approval logic.
    Safe for SINGLE and BULK approval.
    Prevents duplicate SMS and notifications.
    """

    # ---- SAFETY GUARD ----
    if approval.status == "APPROVED":
        return False

    officer = approval.id_request.officer
    profile = officer.profile

    # ---- UPDATE APPROVAL ----
    approval.status = "APPROVED"
    approval.approved_by = approved_by
    approval.date_processed = timezone.now()
    approval.save(update_fields=["status", "approved_by", "date_processed"])

    # ---- QR SETUP (ONLY ONCE) ----
    if not profile.qr_token:
        profile.qr_token = uuid.uuid4().hex[:12].upper()

    profile.is_active_qr = True
    profile.qr_expiry_date = timezone.now() + timedelta(days=365)
    profile.date_approved = timezone.now()
    profile.save(update_fields=[
        "qr_token",
        "is_active_qr",
        "qr_expiry_date",
        "date_approved"
    ])

    # ---- SMS (SEND ONLY ON FIRST APPROVAL) ----
    if send_sms_flag and not profile.sms_sent:
        result = send_qr_link(profile)
        if result.get("success"):
            profile.sms_sent = True
            profile.save(update_fields=["sms_sent"])

    # ---- IN-APP NOTIFICATION ----
    Notification.objects.create(
        user=officer,
        title="ID Request Approved",
        message="Your ID request has been approved. Click to view and print your ID.",
        link=reverse("digital_id:officer_id", args=[officer.staffid]),
    )

    return True
