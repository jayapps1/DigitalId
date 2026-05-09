from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from digital_id.models import OfficerProfile
from .models import PrintRequest

# ------------------------
# Admin / Staff Views
# ------------------------
@staff_member_required
def admin_print_requests(request):
    user = request.user
    role = getattr(user, "role", None)

    if user.is_superuser:
        requests = PrintRequest.objects.all()
    elif role == "REGIONAL_ADMIN":
        requests = PrintRequest.objects.filter(officer__region=user.region)
    elif role == "STATION_ADMIN":
        requests = PrintRequest.objects.filter(officer__station=user.profile.station)
    else:
        return HttpResponseForbidden()

    # Auto-lock expired PRINTED requests in queryset only
    now = timezone.now()
    expired = requests.filter(status="PRINTED", locked_until__lt=now)
    expired.update(status="LOCKED")

    return render(request, "print_id/admin_print_requests.html", {
        "requests": requests,
        "can_manage": user.is_superuser or role == "REGIONAL_ADMIN"
    })


@staff_member_required
def approve_print_request(request, request_id):
    user = request.user
    role = getattr(user, "role", None)

    if user.is_superuser:
        pr = get_object_or_404(PrintRequest, id=request_id)
    elif role == "REGIONAL_ADMIN":
        pr = get_object_or_404(PrintRequest, id=request_id, officer__region=user.region)
    else:
        return HttpResponseForbidden()

    pr.approve(admin_user=user)
    return redirect("print_id:admin_requests")


@staff_member_required
def print_officer_card(request, request_id):
    user = request.user
    role = getattr(user, "role", None)

    # Only Super Admin or Regional Admin can print
    if user.is_superuser:
        pr = get_object_or_404(PrintRequest, id=request_id)
    elif role == "REGIONAL_ADMIN":
        pr = get_object_or_404(PrintRequest, id=request_id, officer__region=user.region)
    else:
        return HttpResponseForbidden()

    # Ensure request is printable
    if not pr.is_printable:
        return render(request, "print_id/print_error.html", {"msg": "Request not printable."})

    # Mark as printed (sets PRINTED + lock)
    pr.mark_printed()
    profile = pr.officer

    return render(request, "digital_id/officer_id.html", {"profile": profile})


# ------------------------
# Officer Views
# ------------------------
@login_required
def officer_print_requests(request):
    try:
        profile = OfficerProfile.objects.get(user__staffid=request.user.staffid)
    except OfficerProfile.DoesNotExist:
        return render(request, "print_id/request_error.html", {
            "msg": "You do not have an Officer Profile assigned. Contact Admin."
        })

    return render(request, "print_id/officer_print_requests.html", {
        "requests": profile.print_requests.all()
    })


@login_required
def request_print_card(request):
    if request.method != "POST":
        return HttpResponseForbidden()

    try:
        profile = OfficerProfile.objects.get(user__staffid=request.user.staffid)
    except OfficerProfile.DoesNotExist:
        return render(request, "print_id/request_error.html", {
            "msg": "You do not have an Officer Profile assigned. Contact Admin."
        })

    temp_request = PrintRequest(officer=profile)

    if not temp_request.can_officer_request():
        return render(request, "print_id/request_error.html", {
            "msg": "You cannot request print at this time."
        })

    PrintRequest.objects.create(
        officer=profile,
        requested_by=request.user,
        status="PENDING"
    )

    return redirect("print_id:officer_requests")