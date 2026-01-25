import requests
from django.conf import settings

def send_sms(phone: str, message: str) -> dict:
    """
    Send an SMS via ArkAcel API.

    Args:
        phone (str): Recipient phone number in E.164 format, e.g., +233XXXXXXXXX
        message (str): Text message to send

    Returns:
        dict: 
            On success: {"success": True, "data": str}
            On failure: {"success": False, "error": str}
    """
    url = "https://sms.arkesel.com/sms/api"

    params = {
        "action": "send-sms",
        "api_key": getattr(settings, "ARKESEL_API_KEY", ""),
        "to": phone,              # Recipient number in E.164
        "from": "KomendaFS",      # Must be pre-approved in ArkAcel
        "sms": message,
    }

    if not params["api_key"]:
        return {"success": False, "error": "ArkAcel API key not set in settings"}

    try:
        response = requests.get(url, params=params, timeout=15)
        text = response.text.strip()  # Clean whitespace/newlines

        # Check HTTP status
        if response.status_code != 200:
            return {"success": False, "error": f"HTTP {response.status_code}: {text}"}

        # ArkAcel success code starts with 1701
        if text.startswith("1701"):
            return {"success": True, "data": text}
        else:
            return {"success": False, "error": f"API returned error: {text}"}

    except requests.RequestException as e:
        return {"success": False, "error": f"Request exception: {str(e)}"}
