import base64
import uuid
import requests
import logging
from decimal import Decimal
from django.conf import settings

from momo_payments.models import MTNPayment
from momo_payments.utils import calculate_mtn_payment

logger = logging.getLogger(__name__)

SANDBOX_BASE_URL = "https://sandbox.momodeveloper.mtn.com"
LIVE_BASE_URL = "https://momodeveloper.mtn.com"


def get_base_url() -> str:
    """
    Returns MTN MoMo API base URL depending on environment
    """
    return SANDBOX_BASE_URL if settings.MTN_MOMO_ENV == "sandbox" else LIVE_BASE_URL


def get_mtn_access_token() -> str:
    """
    Generates MTN MoMo access token using API user ID and primary key
    """
    auth_string = f"{settings.MTN_MOMO_USER_ID}:{settings.MTN_MOMO_PRIMARY_KEY}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
    }

    url = f"{get_base_url()}/collection/token/"

    try:
        response = requests.post(url, headers=headers, timeout=15)
        response.raise_for_status()
        token = response.json().get("access_token")
        logger.info("MTN MoMo access token generated successfully")
        return token
    except requests.RequestException as e:
        logger.error(f"Failed to generate MTN access token: {str(e)}", exc_info=True)
        raise


def initiate_mtn_payment(*, officer, id_request, request_type: str, phone_number: str) -> MTNPayment:
    """
    Creates MTNPayment record and sends request-to-pay to MTN MoMo sandbox/live.
    Returns MTNPayment instance.
    """
    # Calculate payment amount
    base, service_fee, total = calculate_mtn_payment(request_type)

    # Create payment record
    reference = str(uuid.uuid4())
    payment = MTNPayment.objects.create(
        officer=officer,
        id_request=id_request,
        request_type=request_type,
        phone_number=phone_number,
        amount=total,
        currency="EUR" if settings.MTN_MOMO_ENV == "sandbox" else "GHS",
        reference=reference,
    )

    # Send request-to-pay
    try:
        token = get_mtn_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": reference,
            "X-Target-Environment": settings.MTN_MOMO_ENV,
            "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "amount": str(payment.amount),
            "currency": payment.currency,
            "externalId": reference,
            "payer": {"partyIdType": "MSISDN", "partyId": phone_number},
            "payerMessage": "Digital ID Payment",
            "payeeNote": f"ID Request ({request_type})",
        }

        url = f"{get_base_url()}/collection/v2_0/requesttopay"
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        payment.raw_response = response.json() if response.content else {}
        payment.save(update_fields=["raw_response"])

        logger.info(f"MTN MoMo request-to-pay sent successfully: {reference}")
        return payment

    except requests.RequestException as e:
        logger.error(f"MTN MoMo request-to-pay failed: {str(e)}", exc_info=True)
        payment.mark_failed({"error": str(e)})
        raise


def check_mtn_payment_status(payment: MTNPayment) -> dict:
    """
    Polls MTN MoMo to confirm payment status
    """
    try:
        token = get_mtn_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": settings.MTN_MOMO_ENV,
            "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
        }

        url = f"{get_base_url()}/collection/v2_0/requesttopay/{payment.reference}"
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Update raw response
        payment.raw_response = data
        payment.save(update_fields=["raw_response"])

        # Update payment status
        status = data.get("status")
        if status == "SUCCESSFUL":
            payment.mark_success(data)
        elif status == "FAILED":
            payment.mark_failed(data)

        return data

    except requests.RequestException as e:
        logger.error(f"Failed to check MTN payment status: {str(e)}", exc_info=True)
        return {"error": str(e)}
