from digital_id.models import IDRequest



def notifications(request):
    from digital_id.models import Notification
    

    if not request.user.is_authenticated:
        return {}

    if request.user.is_staff or request.user.is_superuser:
        qs = Notification.objects.all()
    else:
        qs = Notification.objects.filter(user=request.user)

    return {
        'unread_notifications_count': qs.filter(is_read=False).count(),
        'notifications': qs.order_by('-created_at')[:5],  # preview only
    }



def pending_requests_count(request):
    if request.user.is_staff or request.user.is_superuser:
        count = IDRequest.objects.filter(approval__status="PENDING").count()
        return {"pending_requests_count": count}
    return {"pending_requests_count": 0}

