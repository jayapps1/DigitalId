# digital_id/utils.py

from .models import IDRequest

def officer_has_pending_request(user):
    return IDRequest.objects.filter(
        officer=user,
        approval__status="PENDING"
    ).exists()

def officer_has_new_request_before(user):
    return IDRequest.objects.filter(
        officer=user,
        request_type="NEW"
    ).exists()
