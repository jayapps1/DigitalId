from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from digital_id.models import Notification
from digital_id.qr_service import send_qr_link
from digital_id.services.digital_id.qr_lifecycle import activate_qr
import uuid


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

    # ---- QR TOKEN (ONLY GENERATE IF MISSING) ----
    if not profile.qr_token:
        profile.qr_token = uuid.uuid4().hex[:12].upper()
        profile.save(update_fields=["qr_token"])

    # ---- ACTIVATE QR (5 YEARS FROM qr_lifecycle) ----
    activate_qr(profile)

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
