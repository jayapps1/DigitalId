# payments/paystack_service.py
import requests
from django.conf import settings
import logging
import hmac
import hashlib

from payments.models import Payment

logger = logging.getLogger(__name__)

def initialize_paystack_payment(payment):
    """
    Initialize a Paystack transaction for the given Payment object.
    Returns the authorization URL for redirecting the officer.
    """

    # Use HTTPS for production, HTTP for local development
    protocol = "https" if not settings.DEBUG else "http"
    callback_url = f"{protocol}://{settings.SITE_URL}/payments/verify/"

    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    # Log basic payment info
    logger.info(
        f"Initializing Paystack payment: reference={payment.reference}, "
        f"officer={payment.officer.staffid}, request_type={payment.request_type}, "
        f"amount={payment.total_amount}"
    )

    # Prepare payload for Paystack
    payload = {
        "email": payment.officer.email,
        "amount": int(round(payment.total_amount * 100)),  # Convert GHS to kobo
        "reference": payment.reference,
        "callback_url": callback_url
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()  # Raise error for HTTP 4xx/5xx
        response_data = response.json()
    except requests.RequestException as e:
        logger.error(f"Network error initializing Paystack payment: {e}", exc_info=True)
        raise Exception("Failed to initialize Paystack payment due to network error")
    except ValueError as e:
        logger.error(f"Invalid JSON response from Paystack: {e}", exc_info=True)
        raise Exception("Failed to parse Paystack response")

    # Validate response
    if not response_data.get("status") or "data" not in response_data or "authorization_url" not in response_data["data"]:
        logger.error(f"Paystack initialization failed: {response_data}")
        raise Exception("Failed to initialize Paystack payment")

    auth_url = response_data["data"]["authorization_url"]
    logger.info(f"Paystack payment initialized successfully: {payment.reference}")
    logger.debug(f"Authorization URL: {auth_url}")

    return auth_url


def verify_paystack_signature(request):
    """
    Verify Paystack webhook signature to ensure the payload is authentic.
    Uses the 'x-paystack-signature' header.
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
    Wrapper for Payment.refund(), keeps service interface.
    """
    return payment.refund(initiated_by=initiated_by)
