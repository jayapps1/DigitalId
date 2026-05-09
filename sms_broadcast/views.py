from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .services import broadcast_sms
from digital_id.models import User, OfficerProfile

from .models import SMSBroadcast, SMSDelivery

@login_required
def send_broadcast(request):
    user = request.user
    role = getattr(user, "role", "USER")  # your role field

    # Scope choices and initial applicable values
    scope_choices = []
    applicable_initial = None
    applicable_readonly = False

    if role == "SUPERADMIN":
        scope_choices = ["ALL", "REGION", "STATION"]
    elif role == "REGIONAL_ADMIN":
        scope_choices = ["REGION"]
        applicable_initial = getattr(user, "region", "")
        applicable_readonly = True
    elif role == "STATION_ADMIN":
        scope_choices = ["STATION"]
        applicable_initial = getattr(user.profile, "station", "")
        applicable_readonly = True

    # Instead of querying models, use choices directly
    regions = User.REGION_CHOICES  # tuple of tuples like ("GREATER_ACC", "Greater Accra")
    stations = OfficerProfile._meta.get_field("station").choices  # FIRE_STATION_CHOICES

    if request.method == "POST":
        message = request.POST.get("message")
        scope = request.POST.get("scope")
        region = request.POST.get("region")
        station = request.POST.get("station")

        try:
            broadcast = broadcast_sms(
                sender=user,
                message=message,
                scope=scope,
                region=region,
                station=station
            )
            messages.success(request, f"Broadcast sent to {broadcast.total_recipients} users.")
        except Exception as e:
            messages.error(request, f"Error sending broadcast: {str(e)}")

        return redirect("sms_broadcast:send_sms")

    return render(request, "sms_broadcast/send_broadcast.html", {
        "role": role,
        "scope_choices": scope_choices,
        "applicable_initial": applicable_initial,
        "applicable_readonly": applicable_readonly,
        "regions": regions,
        "stations": stations,
        "user": user,
    })



@login_required
def broadcast_status(request, broadcast_id):
    broadcast = get_object_or_404(SMSBroadcast, id=broadcast_id)
    deliveries = broadcast.deliveries.all().order_by("-created_at")

    return render(request, "sms_broadcast/broadcast_status.html", {
        "broadcast": broadcast,
        "deliveries": deliveries,
    })

