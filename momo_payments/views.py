from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from momo_payments.services.mtn_momo import initiate_mtn_payment, check_mtn_payment_status
from momo_payments.models import MTNPayment
from digital_id.models import IDRequest

# -------------------------------
# Start MTN Payment (Form or Button)
# -------------------------------
def start_mtn_payment(request, id_request_id):
    id_request = get_object_or_404(IDRequest, pk=id_request_id)
    officer = request.user

    if request.method == "POST":
        phone_number = request.POST.get("phone_number")

        payment = initiate_mtn_payment(
            officer=officer,
            id_request=id_request,
            request_type=id_request.request_type,
            phone_number=phone_number
        )

        # Redirect to a confirmation page
        return redirect("mtn_payment_status", reference=payment.reference)

    return render(request, "mtn_payments/start_payment.html", {"id_request": id_request})

from django.http import JsonResponse

def mtn_payment_status(request, reference):
    payment = get_object_or_404(MTNPayment, reference=reference)

    # Poll MTN sandbox / live for latest status only if JSON
    if request.GET.get("json") == "1":
        data = {
            "status": payment.status,
            "raw_response": payment.raw_response
        }
        return JsonResponse(data)

    # Regular HTML view
    data = check_mtn_payment_status(payment)
    return render(
        request,
        "mtn_payments/payment_status.html",
        {"payment": payment, "status_data": data}
    )
