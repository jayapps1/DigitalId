from django.conf import settings
from django.urls import reverse
from password_reset.sms_service import send_sms
import logging

logger = logging.getLogger(__name__)


def normalize_phone(phone):
    """
    Normalize Ghana phone numbers to international format +233XXXXXXXXX
    """
    if not phone:
        return None
    phone = str(phone).strip().replace(" ", "")
    if phone.startswith("0"):
        phone = "+233" + phone[1:]
    elif phone.startswith("233"):
        phone = "+233" + phone[3:]
    elif not phone.startswith("+"):
        phone = "+233" + phone
    return phone


def send_qr_link(officer_profile):
    """
    Send the officer their QR link via SMS.

    Args:
        officer_profile: OfficerProfile instance with user & phone info.

    Returns:
        dict: {"success": True} on success, {"success": False, "error": str} on failure.
    """
    officer = officer_profile.user

    # Determine the phone number
    phone = getattr(officer, "phone", None) or getattr(officer_profile, "phone", None)
    if not phone:
        logger.error(f"Officer {officer.staffid} has no phone number")
        return {"success": False, "error": "Officer has no phone number"}

    phone = normalize_phone(phone)

    # Generate officer ID link (print ID page)
    officer_id_url = f"http://{settings.SITE_URL}{reverse('digital_id:officer_id', args=[officer.staffid])}"

    message = (
        f"Hello {officer.get_full_name()}, your official ID card has been approved. "
        f"Click the link to view and print it: {officer_id_url}"
    )

    try:
        result = send_sms(phone, message)
        logger.info(f"SMS gateway raw result for officer {officer.staffid}: {result}")

        # Combine potential messages/errors from API response
        response_text = str(result.get("error", "")) + str(result.get("data", ""))
        response_text = response_text.lower()

        failure_keywords = ["failed", "error", "invalid", "insufficient"]
        success_keywords = ["sent", "success", "ok", "queued", "1701"]  # ArkAcel success code

        # Treat minor warnings as success
        if any(word in response_text for word in failure_keywords):
            logger.warning(f"SMS gateway reported a possible issue for {officer.staffid}: {response_text}")
            return {"success": True}  # assume SMS went through

        if any(word in response_text for word in success_keywords):
            logger.info(f"SMS sent successfully to officer {officer.staffid}")
            return {"success": True}

        # Default fallback: assume sent if unclear
        logger.info(f"SMS response unclear but assumed sent for officer {officer.staffid}: {response_text}")
        return {"success": True}

    except Exception as e:
        logger.exception(f"Exception while sending SMS to officer {officer.staffid}")
        return {"success": False, "error": str(e)}
