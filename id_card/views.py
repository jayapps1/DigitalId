from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from decimal import Decimal
from digital_id.models import OfficerProfile, QRScanLog
from .utils import get_client_ip, get_location_from_ip
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json




@csrf_exempt
def verify_id(request, token):
    profile = OfficerProfile.objects.filter(qr_token=token).first()
    if not profile:
        return render(request, "id_card/verify.html", {"error": "Invalid QR token"})

    ip_address = get_client_ip(request)

    scan_log = QRScanLog.objects.create(
        profile=profile,
        scanned_at=timezone.now(),
        ip_address=ip_address,
        latitude=None,
        longitude=None,
    )

    return render(request, "id_card/verify.html", {
        "profile": profile,
        "scan_log_id": scan_log.id,
    })



@csrf_exempt
@require_POST
def update_gps(request):
    try:
        data = json.loads(request.body)
        scan_id = data.get("scan_id")
        latitude = Decimal(str(data.get("latitude"))) if data.get("latitude") else None
        longitude = Decimal(str(data.get("longitude"))) if data.get("longitude") else None

        scan = QRScanLog.objects.get(id=scan_id)
        scan.latitude = latitude
        scan.longitude = longitude
        scan.save()
        return JsonResponse({"success": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def is_superadmin(user):
    return user.is_authenticated and user.is_superuser


@user_passes_test(is_superadmin)
def scan_logs(request):
    logs = QRScanLog.objects.select_related(
        'profile',
        'profile__user'
    ).order_by('-scanned_at')

    return render(request, "id_card/scan_logs.html", {
        "scan_logs": logs
    })


@user_passes_test(is_superadmin)
def scan_detail(request, scan_id):
    scan = get_object_or_404(QRScanLog, id=scan_id)

    return render(request, "id_card/scan_detail.html", {
        "scan": scan
    })
