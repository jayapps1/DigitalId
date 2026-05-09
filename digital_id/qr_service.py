from django.conf import settings
from django.urls import reverse
from password_reset.sms_service import send_sms
import logging

logger = logging.getLogger(__name__)


def normalize_phone(phone):
    """
    Normalize Ghana phone numbers to production format: 233XXXXXXXXX
    (NO + sign – required by most Ghana SMS gateways)
    """
    if not phone:
        return None

    phone = str(phone).strip().replace(" ", "")

    # Remove +
    if phone.startswith("+"):
        phone = phone[1:]

    # Convert 0XXXXXXXXX → 233XXXXXXXXX
    if phone.startswith("0"):
        phone = "233" + phone[1:]

    # Already correct format
    if phone.startswith("233") and len(phone) == 12:
        return phone

    logger.error(f"Invalid phone format after normalization: {phone}")
    return None


def send_qr_link(officer_profile):
    officer = officer_profile.user

    # Resolve phone
    phone = getattr(officer, "phone", None) or getattr(officer_profile, "phone", None)
    if not phone:
        logger.error(f"[SMS] Officer {officer.staffid} has no phone number")
        return {"success": False, "error": "No phone number"}

    phone = normalize_phone(phone)
    if not phone:
        return {"success": False, "error": "Invalid phone format"}

    # QR link
    officer_id_url = f"{settings.SITE_URL}{reverse('digital_id:officer_id', args=[officer.staffid])}"

    message = (
        f"Hello {officer.get_full_name()}, "
        f"your official ID card has been approved. "
        f"View and print it here: {officer_id_url}"
    )

    try:
        result = send_sms(phone, message)
        logger.info(f"[SMS RAW RESPONSE] {result}")

        response_text = (
            str(result.get("status", "")) +
            str(result.get("message", "")) +
            str(result.get("data", "")) +
            str(result.get("error", ""))
        ).lower()

        # ---- SUCCESS CODES FIRST ----
        success_keywords = ["sent", "success", "ok", "queued", "1701"]
        if any(word in response_text for word in success_keywords):
            logger.info(f"[SMS SENT] staffid={officer.staffid}")
            return {"success": True}

        # ---- DEFINITIVE FAILURE ----
        failure_keywords = ["denied", "blocked", "rejected"]
        if any(word in response_text for word in failure_keywords):
            logger.error(f"[SMS FAILED] staffid={officer.staffid} → {response_text}")
            return {"success": False, "error": response_text}

        # ---- UNCLEAR RESPONSE, assume sent (minor warnings) ----
        logger.warning(f"[SMS AMBIGUOUS] staffid={officer.staffid} → {response_text}")
        return {"success": True}

    except Exception as e:
        logger.exception(f"[SMS EXCEPTION] staffid={officer.staffid}")
        return {"success": False, "error": str(e)}
