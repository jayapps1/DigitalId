import uuid
import logging
import json
from decimal import Decimal
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils import timezone
from digital_id.models import IDRequest, IDRequestApproval, User
from .models import Payment
from .utils import calculate_payment
from .paystack_service import initialize_paystack_payment, verify_paystack_signature
import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q
from django.db import transaction



logger = logging.getLogger(__name__)



@login_required
def resume_payment_view(request, staffid):
    """
    Shows the officer their latest unpaid ID request and allows them to resume payment.
    """
    # 1️⃣ Fetch officer by staffid
    officer = get_object_or_404(User, staffid=staffid)

    # 2️⃣ Security check
    if request.user != officer:
        messages.error(request, "You are not authorized to access this request.")
        return redirect("officers_dash:dashboard")

    # 3️⃣ Fetch latest unpaid IDRequest
    id_request = IDRequest.objects.filter(
        officer=officer
    ).filter(
        Q(payment__status__in=["PENDING", "FAILED"]) | Q(payment__isnull=True)
    ).order_by("-date_requested").first()

    if not id_request:
        messages.info(request, "You have no unpaid ID requests to resume.")
        return redirect("officers_dash:dashboard")

    # 4️⃣ Ensure Payment exists
    payment = getattr(id_request, "payment", None)
    if not payment or payment.status not in ["PENDING", "FAILED"]:
        base, service_fee, paystack_fee, total = calculate_payment(id_request.request_type)
        reference = uuid.uuid4().hex.upper()
        payment = Payment.objects.create(
            officer=officer,
            reference=reference,
            request_type=id_request.request_type,
            base_amount=base,
            service_fee=service_fee,
            paystack_fee=paystack_fee,
            total_amount=total,
            status="PENDING",
            id_request=id_request
        )

    # 5️⃣ Render template
    return render(request, "payments/resume_payment.html", {
        "id_request": id_request,
        "payment": payment,
    })


@login_required
def start_new_id_payment(request, request_type):
    user = request.user
    request_type = request_type.upper()
    allowed_types = ["NEW", "LOST", "EXPIRED"]

    if request_type not in allowed_types:
        messages.error(request, f"Invalid request type: {request_type}")
        return redirect("officers_dash:dashboard")

    # Check for existing IDRequest
    id_request = IDRequest.objects.filter(
        officer=user,
        request_type=request_type
    ).filter(
        Q(payment__status__in=["PENDING", "FAILED"]) | Q(payment__isnull=True)
    ).order_by("-date_requested").first()

    if id_request:
        payment = getattr(id_request, "payment", None)
        if payment and payment.status == "PENDING":
            return redirect("payments_sys:resume_payment", staffid=user.staffid)
        elif not payment or payment.status == "FAILED":
            base, service_fee, paystack_fee, total = calculate_payment(request_type)
            payment = Payment.objects.create(
                officer=user,
                reference=uuid.uuid4().hex.upper(),
                request_type=request_type,
                base_amount=base,
                service_fee=service_fee,
                paystack_fee=paystack_fee,
                total_amount=total,
                status="PENDING",
                id_request=id_request
            )
    else:
        # Should never hit here if request_id_view always creates IDRequest
        id_request = IDRequest.objects.create(officer=user, request_type=request_type)
        IDRequestApproval.objects.get_or_create(id_request=id_request)
        base, service_fee, paystack_fee, total = calculate_payment(request_type)
        payment = Payment.objects.create(
            officer=user,
            reference=uuid.uuid4().hex.upper(),
            request_type=request_type,
            base_amount=base,
            service_fee=service_fee,
            paystack_fee=paystack_fee,
            total_amount=total,
            status="PENDING",
            id_request=id_request
        )

    try:
        auth_url = initialize_paystack_payment(payment)
    except Exception as e:
        logger.error(f"Failed to initialize Paystack payment: {e}")
        messages.error(request, "Unable to initialize payment. Please try again later.")
        return redirect("officers_dash:dashboard")

    return redirect(auth_url)


import uuid
from django.db import transaction

@login_required
def resume_payment_paystack(request, payment_id):
    payment = get_object_or_404(
        Payment,
        id=payment_id,
        officer=request.user
    )

    if payment.status == "SUCCESS":
        messages.info(request, "Payment already completed.")
        return redirect("officers_dash:dashboard")

    # 🔒 Email is mandatory for Paystack
    if not payment.officer.email:
        messages.error(request, "No email found on your account.")
        return redirect("officers_dash:dashboard")

    with transaction.atomic():
        # 🔄 Reset transaction context
        payment.reference = uuid.uuid4().hex.upper()
        payment.status = "PENDING"
        payment.paid_at = None
        payment.raw_response = None
        payment.save(
            update_fields=["reference", "status", "paid_at", "raw_response"]
        )

        logger.info(
            f"Re-initializing Paystack payment "
            f"(resume): payment_id={payment.id}, reference={payment.reference}"
        )

        auth_url = initialize_paystack_payment(payment)

        if not auth_url:
            messages.error(request, "Unable to initialize payment.")
            return redirect("officers_dash:dashboard")

    return redirect(auth_url)




@csrf_exempt
def paystack_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    if not verify_paystack_signature(request):
        return HttpResponse(status=400)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if payload.get("event") != "charge.success":
        return HttpResponse(status=200)

    data = payload.get("data", {})
    reference = data.get("reference")
    if not reference:
        return HttpResponse(status=400)

    payment = get_object_or_404(Payment, reference=reference)

    if payment.status == "SUCCESS":
        return HttpResponse(status=200)

    # Mark payment successful
    payment.status = "SUCCESS"
    payment.paid_at = timezone.now()
    payment.raw_response = data
    payment.save(update_fields=["status", "paid_at", "raw_response"])
    logger.info(f"Payment {reference} marked SUCCESS")

    # Send confirmation email
    if payment.officer.email:
        from django.core.mail import send_mail
        try:
            send_mail(
                subject="Payment Successful",
                message=(
                    f"Hello {payment.officer.get_full_name()}, your payment "
                    f"for {payment.request_type} ID request was successful. "
                    "Your request is now pending admin approval."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[payment.officer.email],
            )
            logger.info(f"Payment confirmation email sent to {payment.officer.email}")
        except Exception as e:
            logger.error(f"Failed to send payment email: {e}", exc_info=True)

    return HttpResponse(status=200)



@login_required
def verify_payment(request):
    reference = request.GET.get("reference")
    if not reference:
        messages.error(request, "Invalid payment reference.")
        return redirect("officers_dash:dashboard")

    payment = get_object_or_404(Payment, reference=reference)

    if payment.status == "SUCCESS":
        messages.info(request, "Payment already verified. Your request is pending admin approval.")
        return redirect("officers_dash:dashboard")

    # Verify with Paystack
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}

    try:
        response = requests.get(verify_url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
    except Exception:
        messages.error(request, "Unable to verify payment.")
        return redirect("officers_dash:dashboard")

    if result.get("status") and result["data"]["status"] == "success":
        payment.status = "SUCCESS"
        payment.paid_at = timezone.now()
        payment.save(update_fields=["status", "paid_at"])
        messages.success(request, "Payment successful. Your request is now pending admin approval.")
        return redirect("officers_dash:dashboard")

    messages.error(request, "Payment verification failed.")
    return redirect("officers_dash:dashboard")