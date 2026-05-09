from django.conf import settings
from digital_id.models import User
from .models import SMSBroadcast, SMSDelivery
from password_reset.sms_service import send_sms
from django.utils import timezone

def broadcast_sms(sender, message, scope, region=None, station=None):
    """
    Safely send broadcast SMS to users.
    """
    # -------------------------
    # Determine recipients
    # -------------------------
    recipients = User.objects.none()  # default empty queryset

    try:
        if scope == "ALL":
            if sender.role != "SUPERADMIN":
                raise PermissionError("Only SUPERADMIN can send to ALL users")
            recipients = User.objects.filter(is_active=True)
        elif scope == "REGION":
            if sender.role not in ["SUPERADMIN", "REGIONAL_ADMIN"]:
                raise PermissionError("You cannot send to a region")
            if sender.role == "REGIONAL_ADMIN":
                region = getattr(sender, "region", None)
            recipients = User.objects.filter(is_active=True, region=region)
        elif scope == "STATION":
            if sender.role not in ["SUPERADMIN", "REGIONAL_ADMIN", "STATION_ADMIN"]:
                raise PermissionError("You cannot send to a station")
            if sender.role == "STATION_ADMIN":
                station = getattr(sender.profile, "station", None)
            recipients = User.objects.filter(is_active=True, profile__station=station)
        else:
            raise ValueError("Invalid scope")
    except Exception as e:
        raise ValueError(f"Error determining recipients: {str(e)}")

    total_recipients = recipients.count()

    # -------------------------
    # Create broadcast record
    # -------------------------
    broadcast = SMSBroadcast.objects.create(
        sender=sender,
        message=message,
        scope=scope,
        region=region or None,
        station=station or None,
        total_recipients=total_recipients
    )

    # -------------------------
    # Send SMS safely
    # -------------------------
    sent_count = 0
    failed_count = 0

    for user in recipients:
        try:
            # Safely get phone number
            phone = getattr(user, "phone", None) or getattr(user.profile, "phone", None)
            if not phone:
                failed_count += 1
                continue
            if not phone.startswith("+"):
                phone = f"+{phone}"

            delivery = SMSDelivery.objects.create(
                broadcast=broadcast,
                user=user,
                phone_number=phone
            )

            # send SMS with try/except
            try:
                result = send_sms(phone, message)
            except Exception as e:
                result = {"success": False, "error": str(e)}

            if result.get("success"):
                delivery.status = "SENT"
                delivery.provider_message_id = result.get("data", {}).get("message_id")
                sent_count += 1
            else:
                delivery.status = "FAILED"
                delivery.response_message = result.get("error")
                failed_count += 1

            delivery.sent_at = timezone.now()
            delivery.save()
        except Exception as e:
            # Catch unexpected errors per user
            failed_count += 1
            continue

    # -------------------------
    # Update broadcast counts
    # -------------------------
    broadcast.sent_count = sent_count
    broadcast.failed_count = failed_count
    broadcast.delivered_count = 0
    broadcast.save()

    return broadcast
