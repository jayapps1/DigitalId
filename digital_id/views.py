from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import User, Notification, IDRequest, IDRequestApproval
from .forms import IDRequestForm, AdminOfficerRegistrationForm
from django.utils import timezone
from django.db.models import Q
from .models import User, OfficerProfile
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.http import HttpResponse
from payments.models import Payment
from payments.utils import calculate_payment
import openpyxl
from django.views import View
from django.contrib.auth import get_user_model
import re
from django.db import transaction, models

def Home(request):
    return render(request, "digital_id/index.html")
#admin register view




User = get_user_model()



# -------------------------
# Excel Officer Import View
# -------------------------
class OfficerExcelImportView(View):
    template_name = 'digital_id/import_officer.html'

    def get(self, request):
        return render(request, self.template_name)

    def _safe_str(self, value, upper=False):
        if value is None:
            return None
        value = str(value).strip()
        return value.upper() if upper else value

    def post(self, request):
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, "Please select an Excel file to upload.")
            return redirect('digital_id:import_officer')

        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active
        except Exception:
            messages.error(request, "Invalid Excel file.")
            return redirect('digital_id:import_officer')

        expected_columns = [
            'staffid', 'service_number', 'firstname', 'lastname', 'gender',
            'role', 'region', 'district', 'rank', 'station'
        ]
        header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        if header != expected_columns:
            messages.error(
                request,
                f"Incorrect Excel columns. Expected: {', '.join(expected_columns)}"
            )
            return redirect('digital_id:import_officer')

        created = 0
        updated = 0
        skipped = []

        gender_map = {"MALE": "M", "FEMALE": "F", "M": "M", "F": "F"}
        rank_map = {"NON-COMMISSIONED OFFICER": "NCO", "COMMISSIONED OFFICER": "CO", "NCO": "NCO", "CO": "CO"}
        role_map = {"OFFICER": "OFFICER", "ADMIN OFFICER": "ADMIN", "SYSTEM SUPER ADMIN": "SUPERADMIN"}

        for idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(cell is None for cell in row):
                continue

            (
                staffid, service_number, firstname, lastname, gender,
                role, region, district, rank, station
            ) = row

            staffid = self._safe_str(staffid, upper=True)
            service_number = self._safe_str(service_number, upper=True)

            if not staffid or not service_number:
                skipped.append((idx, "Missing staffid or service_number"))
                continue

            if not re.fullmatch(r'GF\d{6}D', service_number):
                skipped.append((idx, f"Invalid service number: {service_number}"))
                continue

            gender_code = gender_map.get(self._safe_str(gender, upper=True))
            if not gender_code:
                skipped.append((idx, f"Invalid gender: {gender}"))
                continue

            try:
                with transaction.atomic():
                    # Update or create user
                    user, is_created = User.objects.update_or_create(
                        staffid=staffid,
                        defaults={
                            "service_number": service_number,
                            "firstname": self._safe_str(firstname),
                            "lastname": self._safe_str(lastname),
                            "gender": gender_code,
                            "role": role_map.get(self._safe_str(role, upper=True), "OFFICER"),
                            "region": self._safe_str(region),
                            "district": self._safe_str(district),
                        }
                    )
                    if is_created:
                        user.set_password("Officer@123")
                        user.save()
                        created += 1
                    else:
                        updated += 1

                    # Update or create OfficerProfile
                    OfficerProfile.objects.update_or_create(
                        user=user,
                        defaults={
                            "rank": rank_map.get(self._safe_str(rank, upper=True), "NCO"),
                            "station": self._safe_str(station),
                        }
                    )

            except Exception as e:
                skipped.append((idx, str(e)))

        message = f"{created} officers created, {updated} officers updated."
        if skipped:
            message += f" {len(skipped)} rows skipped.\n"
            for row_num, reason in skipped:
                message += f"Row {row_num}: {reason}\n"

        messages.success(request, message)
        return redirect('digital_id:import_officer')


# -------------------------
# Officer ID / Print Page
# -------------------------
def officer_id(request, staffid):
    profile = get_object_or_404(OfficerProfile, user__staffid=staffid)
    return render(request, "digital_id/officer_id.html", {
        "profile": profile,
        "hide_qr": False,
        "is_verify_view": False,
    })





# -------------------------
# Admin check decorator
# -------------------------
def is_admin(user):
    return user.is_authenticated and user.role in ["ADMIN", "SUPERADMIN"]


# -------------------------
# Officer registration view
# -------------------------
@login_required
@user_passes_test(is_admin)
def register_officer(request):
    if request.method == "POST":
        form = AdminOfficerRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except IntegrityError as e:
                form.add_error(None, f"Registration failed: Duplicate entry ({str(e)})")
            else:
                messages.success(
                    request,
                    "Officer registered successfully. Default password assigned if none provided."
                )
                return redirect("digital_id:register_officer")
    else:
        form = AdminOfficerRegistrationForm()

    return render(request, "digital_id/register_officer.html", {"form": form})


@login_required
def request_id_view(request):
    user = request.user
    profile = user.profile

    if not user.profile_completed:
        messages.error(request, "You must complete your profile before requesting a new ID card.")
        return redirect("officers_dash:complete_profile")

    unpaid_request = IDRequest.objects.filter(
        officer=user
    ).filter(
        Q(payment__status__in=["PENDING", "FAILED"]) | Q(payment__isnull=True)
    ).order_by("-date_requested").first()

    if unpaid_request:
        messages.warning(request, "You have a pending payment. Please complete it before requesting a new ID.")
        return redirect("payments_sys:resume_payment", staffid=user.staffid)

    has_new = IDRequest.objects.filter(officer=user, request_type="NEW").exists()

    if not has_new:
        allowed_types = ["NEW"]
    else:
        allowed_types = ["LOST"]
        if profile.qr_expiry_date and profile.qr_expiry_date <= timezone.now():
            allowed_types = ["EXPIRED"]

    if request.method == "POST":
        form = IDRequestForm(request.POST, user=user)
        if form.is_valid():
            request_type = form.cleaned_data["request_type"]
            if request_type not in allowed_types:
                messages.error(request, "Invalid request type selection.")
                return redirect("digital_id:request_id")

            # 🔹 Create new IDRequest and Approval immediately
            id_request = IDRequest.objects.create(
                officer=user,
                request_type=request_type
            )
            IDRequestApproval.objects.get_or_create(id_request=id_request)

            # Deactivate QR until approval
            profile.is_active_qr = False
            profile.save(update_fields=["is_active_qr"])

            # Redirect to payment
            return redirect("payments_sys:start_new_id_payment", request_type=id_request.request_type)
    else:
        form = IDRequestForm(user=user)

    request_list = IDRequest.objects.filter(
        officer=user
    ).select_related("payment", "approval").order_by("-date_requested")

    has_pending_request = request_list.filter(
        payment__status="SUCCESS",
        approval__status="PENDING"
    ).exists()

    has_paid = request_list.filter(payment__status="SUCCESS").exists()

    return render(request, "digital_id/idrequest_form.html", {
        "form": form,
        "allowed_types": allowed_types,
        "id_requests": request_list,
        "unpaid_request": unpaid_request,
        "has_pending_request": has_pending_request,
        "has_paid": has_paid,
        "profile": profile,
    })



def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome, {user.firstname}")

            # Force officers to change default password
            if user.is_officer and user.must_change_password:
                Notification.objects.create(
                    user=user,
                    message="You must change your default password before proceeding."
                )
                return redirect("digital_id:change_password")

            # Role-based redirects
            if user.is_superuser:
                return redirect("/admin/admin-dash")
            elif user.is_staff or user.is_officer:
                return redirect("officers_dash:dashboard")
            else:
                messages.error(request, "Access denied.")
                logout(request)
                return redirect("digital_id:login")
        else:
            messages.error(request, "Invalid credentials.")
    else:
        form = AuthenticationForm()

    return render(request, "digital_id/login.html", {"form": form})



@login_required
def change_password(request):
    user = request.user

    # Determine if this is an officer forced to change password
    is_officer = getattr(user, "is_officer", False)

    if request.method == "POST":
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            # Only reset must_change_password for officers
            if is_officer:
                user.must_change_password = False
                user.save(update_fields=["must_change_password"])

            # Keep the user logged in
            update_session_auth_hash(request, user)

            # Optional: create notification for officer only
            if is_officer:
                Notification.objects.create(
                    user=user,
                    message="Your password has been successfully updated."
                )

            messages.success(request, "Password updated successfully.")

            # Redirect based on profile completion (officers only)
            if is_officer and not user.profile_completed:
                return redirect("officers_dash:complete_profile")
            
            # Redirect to dashboard based on user type
            if user.is_staff or user.is_superuser:
                return redirect("admin_dash:home")
            else:
                return redirect("officers_dash:dashboard")

        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(user)

    return render(request, "digital_id/change_password.html", {"form": form})




from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


def user_logout(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('digital_id:login')

class NotificationsView(LoginRequiredMixin, TemplateView):
    template_name = 'digital_id/notifications.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_staff or user.is_superuser:
            notifications = Notification.objects.select_related(
                "user"
            ).order_by("-created_at")

            # mark all as read for admin
            Notification.objects.filter(is_read=False).update(is_read=True)

        else:
            notifications = Notification.objects.select_related(
                "user"
            ).filter(
                user__staffid=user.staffid
            ).order_by("-created_at")

            # mark officer notifications as read
            Notification.objects.filter(
                user__staffid=user.staffid,
                is_read=False
            ).update(is_read=True)

        context["notifications"] = notifications
        return context
    

from django.views.decorators.http import require_POST

@login_required
def view_notification(request, pk):
    """
    View a single notification in detail.

    - Staff/superuser can view all notifications.
    - Regular users can only view their own notifications.
    - Marks notification as read.
    - Redirects to link if specified, otherwise renders detail page.
    """
    # Filter notifications by user unless staff/superuser
    if request.user.is_staff or request.user.is_superuser:
        note = get_object_or_404(Notification, pk=pk)
    else:
        note = get_object_or_404(Notification, pk=pk, user=request.user)

    # Mark as read
    if not note.is_read:
        note.is_read = True
        note.save(update_fields=["is_read"])

    # Redirect to external link if exists
    if note.link:
        return redirect(note.link)

    # Render detail page if no link
    return render(request, "digital_id/notification_detail.html", {"note": note})


@login_required
def delete_notification(request, pk):
    note = get_object_or_404(Notification, pk=pk)
    if not (request.user.is_staff or request.user.is_superuser) and note.user != request.user:
        return redirect("digital_id:notifications")
    note.delete()
    return redirect("digital_id:notifications")


@login_required
@require_POST
def bulk_delete_notifications(request):
    ids = request.POST.getlist("notification_ids")
    if request.user.is_staff or request.user.is_superuser:
        Notification.objects.filter(id__in=ids).delete()
    else:
        Notification.objects.filter(id__in=ids, user=request.user).delete()
    return redirect("digital_id:notifications")


from django.http import JsonResponse



@login_required
def mark_as_read(request, pk):
    """Mark a single notification as read via AJAX."""
    note = Notification.objects.filter(pk=pk, user=request.user).first()
    if note and not note.is_read:
        note.is_read = True
        note.save(update_fields=['is_read'])
    return JsonResponse({'success': True})

@login_required
def get_unread_count(request):
    """Return unread notifications count via AJAX."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})
