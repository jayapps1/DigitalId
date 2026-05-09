from digital_id.models import ContactMessage, Notification, IDRequest

def navbar_counts(request):
    if not request.user.is_authenticated:
        return {}

    user = request.user

    # -------------------------
    # Role-aware notifications
    # -------------------------
    if user.role == "SUPERADMIN":
        qs = Notification.objects.all()

    elif user.role == "REGIONAL_ADMIN" and user.region:
        qs = Notification.objects.filter(user__region=user.region)

    elif (
        user.role == "STATION_ADMIN"
        and hasattr(user, "profile")
        and user.profile.station
    ):
        qs = Notification.objects.filter(
            user__profile__station=user.profile.station
        )

    else:
        qs = Notification.objects.filter(user=user)

    return {
        "dropdown_notifications": qs.order_by("-created_at")[:5],
        "unread_notifications_count": qs.filter(is_read=False).count(),
        "pending_requests_count": (
            IDRequest.objects.filter(approval__status="PENDING").count()
            if user.role in ["SUPERADMIN", "REGIONAL_ADMIN", "STATION_ADMIN"]
            else 0
        ),
        "unread_messages_count": (
            ContactMessage.objects.filter(is_read=False).count()
            if user.role == "SUPERADMIN"
            else 0
        ),
    }
