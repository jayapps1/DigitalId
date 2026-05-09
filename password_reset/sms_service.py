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
            On success: {"success": True, "data": dict}
            On failure: {"success": False, "error": str}
    """
    url = "https://sms.arkesel.com/sms/api"

    params = {
        "action": "send-sms",
        "api_key": getattr(settings, "ARKESEL_API_KEY", ""),
        "to": phone,
        "from": "KomendaFS",
        "sms": message,
    }

    if not params["api_key"]:
        return {"success": False, "error": "ArkAcel API key not set in settings"}

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Try to parse JSON response
        try:
            data = response.json()
        except ValueError:
            return {"success": False, "error": f"Invalid response: {response.text}"}

        # Check API success code
        if data.get("code") == "ok":
            return {"success": True, "data": data}
        else:
            return {"success": False, "error": data.get("message", "Unknown error")}

    except requests.RequestException as e:
        return {"success": False, "error": f"Request exception: {str(e)}"}
