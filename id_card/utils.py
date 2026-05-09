#id_card/utils.py
import requests

def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip

def get_location_from_ip(ip):
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/")
        data = response.json()
        return (
            data.get("latitude"),
            data.get("longitude"),
            data.get("city"),
            data.get("region"),
            data.get("country_name")
        )
    except:
        return None, None, None, None, None
