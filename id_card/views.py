# digital_id/views.py
from django.shortcuts import render, get_object_or_404
from digital_id.models import OfficerProfile, User

def verify_id(request, token):
    try:
        profile = OfficerProfile.objects.get(qr_token=token)
        is_officer = True
    except OfficerProfile.DoesNotExist:
        # fallback: maybe admin user
        profile = get_object_or_404(User, qr_token=token)
        is_officer = False

    return render(request, "id_card/verify.html", {
        "profile": profile,
        "hide_qr": True,
        "is_verify_view": True,
        "is_officer": is_officer,
    })
