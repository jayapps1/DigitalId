# payments/paystack_service.py
import requests
from django.conf import settings
import logging
import hmac
import hashlib

from payments.models import Payment

logger = logging.getLogger(__name__)

from django.conf import settings

def get_callback_url():
    """
    Returns the full callback URL for Paystack.
    Uses PythonAnywhere domain if available, otherwise local dev.
    """
    # Ensure SITE_URL is set in settings or WSGI environment
    site_url = getattr(settings, "SITE_URL", None) or "skiliteent.pythonanywhere.com"

    # Use HTTPS on PythonAnywhere, otherwise fallback to HTTP for dev
    protocol = "https" if "pythonanywhere.com" in site_url else "http"

    return f"{protocol}://{site_url}/payments/verify/"



def initialize_paystack_payment(payment: Payment):
    """
    Initialize a Paystack transaction for the given Payment object.
    Returns the authorization URL for redirecting the officer.
    """
    callback_url = get_callback_url()

    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    logger.info(
        f"Initializing Paystack payment: reference={payment.reference}, "
        f"officer={payment.officer.staffid}, request_type={payment.request_type}, "
        f"amount={payment.total_amount}"
    )

    payload = {
        "email": payment.officer.email,
        "amount": int(round(payment.total_amount * 100)),  # Convert GHS to kobo
        "reference": payment.reference,
        "callback_url": callback_url
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        response_data = response.json()
    except requests.RequestException as e:
        logger.error(f"Network error initializing Paystack payment: {e}", exc_info=True)
        raise Exception("Failed to initialize Paystack payment due to network error")
    except ValueError as e:
        logger.error(f"Invalid JSON response from Paystack: {e}", exc_info=True)
        raise Exception("Failed to parse Paystack response")

    if not response_data.get("status") or "data" not in response_data or "authorization_url" not in response_data["data"]:
        logger.error(f"Paystack initialization failed: {response_data}")
        raise Exception("Failed to initialize Paystack payment")

    auth_url = response_data["data"]["authorization_url"]
    logger.info(f"Paystack payment initialized successfully: {payment.reference}")
    logger.debug(f"Authorization URL: {auth_url}")

    return auth_url


def verify_paystack_signature(request):
    """
    Verify Paystack webhook signature to ensure authenticity.
    Returns True if signature matches, False otherwise.
    """
    signature = request.headers.get("x-paystack-signature", "")
    if not signature:
        logger.warning("No x-paystack-signature header found")
        return False

    secret = settings.PAYSTACK_SECRET_KEY.encode("utf-8")
    computed_signature = hmac.new(secret, request.body, hashlib.sha512).hexdigest()

    if not hmac.compare_digest(computed_signature, signature):
        logger.warning("Paystack webhook signature mismatch")
        return False

    logger.info("Paystack webhook signature verified successfully")
    return True


def initiate_paystack_refund(payment: Payment, initiated_by=None):
    """
    Wrapper for Payment.refund(), keeps service interface consistent.
    """
    return payment.refund(initiated_by=initiated_by)
