# password_reset/views.py
import random
from datetime import timedelta

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from .models import PasswordResetOTP
from .forms import PasswordResetRequestForm, OTPForm, SetPasswordForm
from digital_id.models import User
from .sms_service import send_sms  # ArkAcel SMS service


# -------------------------------------------------
# Helper: normalize Ghana phone number
# -------------------------------------------------
def normalize_ghana_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "")
    if phone.startswith("0"):
        return "+233" + phone[1:]
    if phone.startswith("233"):
        return "+233" + phone[3:]
    if not phone.startswith("+233"):
        return "+233" + phone
    return phone


# -------------------------------------------------
# Step 1: Request OTP
# -------------------------------------------------
def forgot_password(request):
    form = PasswordResetRequestForm(request.POST or None)

    if form.is_valid():
        service_number_input = form.cleaned_data["service_number"].strip()
        phone_input = normalize_ghana_phone(form.cleaned_data["phone"])
        phone_last9 = phone_input[-9:]  # Ghana local digits

        try:
            user = User.objects.get(
                service_number__iexact=service_number_input,
                phone__endswith=phone_last9,
                is_active=True,
            )
        except User.DoesNotExist:
            messages.error(
                request,
                "Service number and phone number do not match our records."
            )
            return render(request, "password_reset/forgot_password.html", {"form": form})

        # Invalidate old OTPs
        PasswordResetOTP.objects.filter(user=user, used=False).update(used=True)

        # Generate new OTP
        otp = str(random.randint(100000, 999999))
        PasswordResetOTP.objects.create(user=user, otp=otp)

        # Send OTP via ArkAcel SMS
        sms_message = f"Your GNFS OTP is {otp}. It is valid for 5 minutes."
        sms_result = send_sms(phone_input, sms_message)
        print("SEND_SMS RESULT:", sms_result)  # log API response

        # Robust success check
        sms_data = sms_result.get("data", "") or ""
        sms_data_clean = sms_data.strip()

        if sms_result.get("success") or sms_data_clean.startswith("1701"):
            messages.success(request, "OTP sent to your registered phone number.")
        else:
            # Log for debugging, but don’t show warning to users
            print("SMS Error Response:", sms_result)
            messages.success(
                request,
                "OTP has been generated and is ready to use."
            )

        # Store user in session
        request.session["reset_user"] = user.staffid
        return redirect("password_reset:verify_otp")

    # Form invalid
    print("FORM ERRORS:", form.errors)
    return render(request, "password_reset/forgot_password.html", {"form": form})


# -------------------------------------------------
# Step 2: Verify OTP
# -------------------------------------------------
def verify_otp(request):
    staffid = request.session.get("reset_user")
    if not staffid:
        return redirect("password_reset:forgot_password")

    form = OTPForm(request.POST or None)

    otp_obj = (
        PasswordResetOTP.objects
        .filter(user__staffid=staffid, used=False)
        .order_by("-created_at")
        .first()
    )

    if form.is_valid():
        if not otp_obj:
            messages.error(request, "No valid OTP found. Please request a new one.")
        elif timezone.now() > otp_obj.created_at + timedelta(minutes=5):
            messages.error(request, "OTP expired. Please request a new one.")
        elif form.cleaned_data["otp"] == otp_obj.otp:
            otp_obj.used = True
            otp_obj.save()
            request.session["otp_verified"] = True
            return redirect("password_reset:set_new_password")
        else:
            messages.error(request, "Invalid OTP.")

    return render(request, "password_reset/verify_otp.html", {"form": form})


# -------------------------------------------------
# Step 3: Set New Password
# -------------------------------------------------
def set_new_password(request):
    if not request.session.get("otp_verified"):
        return redirect("password_reset:forgot_password")

    staffid = request.session.get("reset_user")

    try:
        user = User.objects.get(staffid=staffid, is_active=True)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect("password_reset:forgot_password")

    form = SetPasswordForm(request.POST or None)

    if form.is_valid():
        user.set_password(form.cleaned_data["password1"])
        user.must_change_password = False
        user.save()
        request.session.flush()
        messages.success(request, "Password reset successful. You can now log in.")
        return redirect("digital_id:login")

    return render(request, "password_reset/set_new_password.html", {"form": form})

# password_reset/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def resend_otp(request):
    staffid = request.session.get("reset_user")
    if not staffid:
        return JsonResponse({"success": False, "error": "Session expired"})

    try:
        user = User.objects.get(staffid=staffid, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": "User not found"})

    # Invalidate old OTPs
    PasswordResetOTP.objects.filter(user=user, used=False).update(used=True)

    # Generate new OTP
    import random
    otp = str(random.randint(100000, 999999))
    PasswordResetOTP.objects.create(user=user, otp=otp)

    # Send SMS
    from .sms_service import send_sms
    phone_input = "+233" + user.phone[-9:]  # assuming phone stored like in views
    sms_message = f"Your GNFS OTP is {otp}. It is valid for 5 minutes."
    sms_result = send_sms(phone_input, sms_message)
    print("RESEND_SMS RESULT:", sms_result)

    return JsonResponse({"success": True})

