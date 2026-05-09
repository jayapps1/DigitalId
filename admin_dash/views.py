from django.views.generic import ListView, DetailView, UpdateView, DeleteView, View, CreateView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse
from digital_id.models import User, OfficerProfile, Notification
from .mixins import AdminRequiredMixin, LoginRequiredMixin, UserPassesTestMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test
import base64
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from digital_id.models import IDRequestApproval,  IDRequest, User, ContactMessage
import uuid
from django.core.exceptions import PermissionDenied
from collections import defaultdict
from officers_dash.forms import OfficerUserUpdateForm, OfficerSelfUpdateForm, AdminOfficerUpdateForm
from django.templatetags.static import static
from digital_id.services.digital_id.qr_lifecycle import activate_qr
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from digital_id.forms import IDRequestForm
from digital_id.qr_service import send_qr_link
import logging
from payments.models import Payment
from payments.paystack_service import initiate_paystack_refund
from django.db.models.functions import Lower, Concat
from django.db.models import F, Value
from django.contrib.auth import get_user_model
from password_reset.sms_service import send_sms
from .forms import SuperUserCreationForm, OfficerRoleAssignForm
from .mixins import SuperAdminRequiredMixin  # the mixin above
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from digital_id.models import OfficerProfile
from digital_id.services.digital_id.qr_lifecycle import activate_qr




logger = logging.getLogger(__name__)
User = get_user_model()




# views.py





@login_required
@user_passes_test(lambda u: u.is_superuser or u.role == "REGIONAL_ADMIN")
def assign_officer_role(request):
    preselected_officer = request.GET.get("officer")  # Get officer ID from query param

    if request.method == "POST":
        form = OfficerRoleAssignForm(request.POST, request=request)
        if form.is_valid():
            officer = form.cleaned_data['officer']
            role = form.cleaned_data['role']

            # Update role and flags
            officer.role = role
            officer.is_staff = role in ["SUPERADMIN", "REGIONAL_ADMIN", "STATION_ADMIN"]
            officer.is_superuser = role == "SUPERADMIN"
            officer.save()

            messages.success(request, f"{officer.firstname} {officer.lastname} role updated to {role}.")
            return redirect('admin_dash:assign_officer_role')
    else:
        form = OfficerRoleAssignForm(request=request)

        # Preselect officer if query param exists
        if preselected_officer:
            try:
                officer_instance = User.objects.get(staffid=preselected_officer)
                # Only preselect if the current user has permission
                if (request.user.is_superuser or
                    (request.user.role == "REGIONAL_ADMIN" and officer_instance.region == request.user.region and officer_instance.role != "SUPERADMIN")):
                    form.fields['officer'].initial = officer_instance
            except User.DoesNotExist:
                pass  # ignore invalid IDs

    return render(request, "admin_dash/assign_role.html", {"form": form})



def superadmin_required(user):
    return user.is_authenticated and user.is_superuser


@require_POST
@user_passes_test(superadmin_required)
def bulk_mark_read(request):
    ids = request.POST.getlist("selected_messages")

    if ids:
        ContactMessage.objects.filter(id__in=ids, is_read=False).update(is_read=True)
        messages.success(request, f"{len(ids)} message(s) marked as read.")
    else:
        messages.warning(request, "No messages selected.")

    return redirect("admin_dash:contactmessage_list")


@require_POST
@user_passes_test(superadmin_required)
def bulk_delete(request):
    ids = request.POST.getlist("selected_messages")

    if ids:
        ContactMessage.objects.filter(id__in=ids).delete()
        messages.success(request, f"{len(ids)} message(s) deleted.")
    else:
        messages.warning(request, "No messages selected.")

    return redirect("admin_dash:contactmessage_list")


# admin_dash/views.py

class CreateSuperUserView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = SuperUserCreationForm
    template_name = "admin_dash/create_superuser.html"
    success_url = "/admin/"

    def test_func(self):
        return self.request.user.is_superuser


class AdminHomeView(AdminRequiredMixin, ListView):
    model = User
    template_name = "admin_dash/admin_home.html"
    context_object_name = "officers"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # 1️⃣ Base queryset
        qs = User.objects.filter(is_active=True)

        # 2️⃣ Role-based scoping
        if user.role == "STATION_ADMIN":
            qs = qs.filter(profile__station__iexact=user.profile.station)

        elif user.role == "REGIONAL_ADMIN":
            qs = qs.filter(region=user.region)

        elif user.role == "SUPERADMIN":
            pass

        else:
            return User.objects.none()

        # 3️⃣ Live search (refine the scoped queryset)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(firstname__icontains=q) |
                Q(lastname__icontains=q) |
                Q(staffid__icontains=q)
            )

        # 4️⃣ Annotation + ordering
        return (
            qs.select_related("profile")
              .annotate(
                  full_name=Concat(
                      F("firstname"),
                      Value(" "),
                      F("lastname")
                  )
              )
              .order_by(Lower("full_name"))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = context.get("page_obj")
        context["start_index"] = (page.number - 1) * self.paginate_by if page else 0
        return context




class AdminOfficerDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "admin_dash/officer_detail.html"
    slug_field = "staffid"
    slug_url_kwarg = "staffid"

    def get_object(self, queryset=None):
        staffid = self.kwargs.get("staffid")
        user = self.request.user

        # Admin / Superuser → can view ANY user
        if user.is_staff or user.is_superuser:
            return get_object_or_404(User, staffid=staffid)

        # Normal officer → can view ONLY self
        return get_object_or_404(User, staffid=user.staffid)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_admin_view"] = self.request.user.is_staff or self.request.user.is_superuser
        context["is_self"] = self.request.user == self.object
        return context



class AdminOfficerEditView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "admin_dash/officer_edit.html"
    slug_field = "staffid"
    slug_url_kwarg = "staffid"

    def get_object(self, queryset=None):
        staffid = self.kwargs.get("staffid")
        target = get_object_or_404(User, staffid=staffid)
        user = self.request.user

        # ✅ ALWAYS allow self-edit FIRST
        if target == user:
            return target

        # SUPERUSER can edit everyone
        if user.is_superuser:
            return target

        # REGIONAL_ADMIN can edit anyone in their region except SUPERADMIN
        if user.role == "REGIONAL_ADMIN":
            if target.role == "SUPERADMIN":
                raise PermissionDenied("You cannot edit a Superuser.")

            if target.region != user.region:
                raise PermissionDenied("You can only edit users within your region.")

            return target

        # STATION_ADMIN can only edit officers in their station
        if user.role == "STATION_ADMIN":
            if (
                target.role != "OFFICER"
                or not hasattr(target, "profile")
                or target.profile.station != user.profile.station
            ):
                raise PermissionDenied("You can only edit officers in your station.")
            return target

        raise PermissionDenied("You do not have permission to edit this user.")


    def get_form_class(self):
        user = self.request.user

        # Superadmin gets full admin update form
        if user.is_superuser:
            return AdminOfficerUpdateForm

        # Regional/station admin gets normal officer update form
        elif user.role in ["REGIONAL_ADMIN", "STATION_ADMIN"]:
            return OfficerUserUpdateForm

        # Regular officer edits themselves
        return OfficerSelfUpdateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # Ensure object exists
        self.object = self.get_object()

        # Create or get profile for the user being edited
        profile, _ = OfficerProfile.objects.get_or_create(user=self.object)

        kwargs["profile_instance"] = profile
        kwargs["request"] = self.request  # Required for AdminOfficerUpdateForm
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.object, "profile", None)

        if profile and profile.photo:
            context["photo_url"] = profile.photo.url
        else:
            context["photo_url"] = static(
                "officers_dash/male.JPG" if self.object.gender == "M" else "officers_dash/female.JPG"
            )
        return context

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or user.role in ["REGIONAL_ADMIN", "STATION_ADMIN"]:
            return reverse_lazy("admin_dash:home")
        return reverse_lazy("officers_dash:dashboard")




class AdminOfficerDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = "admin_dash/officer_delete.html"
    slug_field = "staffid"
    slug_url_kwarg = "staffid"
    success_url = reverse_lazy("admin_dash:home")

    def get_object(self, queryset=None):
        staffid = self.kwargs.get("staffid")
        obj = get_object_or_404(User, staffid=staffid)
        user = self.request.user

        # Prevent deleting yourself
        if obj == user:
            raise PermissionDenied("You cannot delete your own account.")

        # Superuser can delete anyone
        if user.is_superuser:
            return obj

        # Regional admin cannot delete superuser
        if user.role == "REGIONAL_ADMIN":
            if obj.role == "SUPERADMIN":
                raise PermissionDenied("You cannot delete a Superuser.")
            return obj

        # Station admin restrictions
        if user.role == "STATION_ADMIN":
            if obj.role != "OFFICER":
                raise PermissionDenied("Station Admin can only delete officers in their station.")
            if obj.profile.station != user.profile.station:
                raise PermissionDenied("You can only delete officers in your station.")
            return obj

        # Default: deny access
        raise PermissionDenied("You do not have permission to delete this user.")




# -------------------
# List all messages
# -------------------
class ContactMessageListView(SuperAdminRequiredMixin, ListView):
    model = ContactMessage
    template_name = "admin_dash/contactmessage_list.html"
    context_object_name = "contact_messages"
    ordering = ["-created_at"]
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        # only show messages for this user if not superuser
        if not self.request.user.is_superuser:
            qs = qs.filter(user=self.request.user)
        return qs


# -------------------
# View a single message
# -------------------


class ContactMessageDetailView(SuperAdminRequiredMixin, DetailView):
    model = ContactMessage
    template_name = "admin_dash/contactmessage_detail.html"
    context_object_name = "message"

    def get(self, request, *args, **kwargs):
        message = self.get_object()
        if not message.is_read:
            message.is_read = True
            message.save()
        return super().get(request, *args, **kwargs)


# -------------------
# Delete a message
# -------------------
class ContactMessageDeleteView(SuperAdminRequiredMixin, DeleteView):
    model = ContactMessage
    template_name = "admin_dash/contactmessage_confirm_delete.html"
    success_url = reverse_lazy("admin_dash:contactmessage_list")



class RegenerateQRView(AdminRequiredMixin, View):
    def post(self, request, staffid):
        profile = get_object_or_404(OfficerProfile, user__staffid=staffid)

        # Delete existing QR image
        if profile.qr_image:
            profile.qr_image.delete(save=False)

        # Generate a new token
        profile.qr_token = uuid.uuid4().hex[:12].upper()

        # Force regeneration of QR image
        profile.qr_image = None
        profile.save()

        return redirect("admin_dash:home")



# -------------------------
# Print QR (Function View)
# -------------------------
def admin_print_qr(request, staffid):
    profile = get_object_or_404(OfficerProfile, user__staffid=staffid)

    response = HttpResponse(content_type="text/html")
    response.write(f"""
        <html>
        <head>
            <title>Print QR</title>
            <style>
                body {{
                    text-align: center;
                    margin: 20px;
                    font-family: Arial, sans-serif;
                }}

                h2 {{
                    margin: 0 0 6px 0;
                    font-size: 20px;
                    letter-spacing: 1px;
                }}

                img {{
                    width: 260px;
                    margin-top: 0;
                    display: block;
                    margin-left: auto;
                    margin-right: auto;
                }}
            </style>
        </head>
        <body onload="window.print()">

            <img src="{profile.qr_image.url}">
        </body>
        </html>
    """)
    return response


@staff_member_required
def admin_id_request_list(request):
    approvals = (
        IDRequestApproval.objects
        .select_related("id_request", "id_request__officer")
        .order_by("-id_request__date_requested")
    )

    grouped_approvals = defaultdict(list)

    for approval in approvals:
        officer = approval.id_request.officer
        grouped_approvals[officer].append(approval)

    context = {
        "grouped_approvals": dict(grouped_approvals)
    }

    return render(
        request,
        "admin_dash/id_request_list.html",
        context
    )



@staff_member_required
def admin_id_request_detail(request, staffid):
    """
    Admin detail view for approving or rejecting ID requests.
    Sends BOTH SMS and in-app notification on approval.
    """
    officer = get_object_or_404(User, staffid=staffid)

    approval = (
        IDRequestApproval.objects
        .select_related(
            "id_request",
            "id_request__officer",
            "id_request__officer__profile",
            "id_request__payment",
        )
        .filter(id_request__officer=officer)
        .order_by("-id_request__date_requested")
        .first()
    )

    if not approval:
        messages.warning(request, f"No ID requests found for officer {staffid}.")
        return redirect("admin_dash:admin_id_request_list")

    payment = getattr(approval.id_request, "payment", None)
    if not payment or payment.status != "SUCCESS":
        messages.error(
            request,
            "This request cannot be processed because payment is not completed."
        )
        return redirect("admin_dash:admin_id_request_list")

    if request.method == "POST":
        action = request.POST.get("action")

        if approval.status != "PENDING":
            messages.warning(request, "This request has already been processed.")
            return redirect("admin_dash:admin_id_request_list")

        if action not in ("APPROVED", "REJECTED"):
            messages.error(request, "Invalid action.")
            return redirect(
                "admin_dash:admin_id_request_detail",
                staffid=officer.staffid
            )

        # UPDATE APPROVAL
        approval.status = action
        approval.approved_by = request.user
        approval.date_processed = timezone.now()
        approval.save()

        profile = officer.profile  # always get profile here

        # =====================================================
        # APPROVAL FLOW
        # =====================================================
        if action == "APPROVED":
            # Ensure QR token exists
            if not profile.qr_token:
                profile.qr_token = uuid.uuid4().hex[:12].upper()
                profile.save(update_fields=["qr_token"])

            # Always activate QR (5 years expiry for both new & existing)
            activate_qr(profile, approved_by=request.user)

            # ---------- SMS ----------
            sms_result = send_qr_link(profile)
            if sms_result.get("success"):
                messages.success(
                    request,
                    f"Approval SMS sent to officer {officer.staffid}."
                )
            else:
                messages.error(
                    request,
                    f"SMS failed: {sms_result.get('error')}"
                )

            # ---------- In-app Notification ----------
            Notification.objects.create(
                user=officer,
                title="ID Request Approved",
                message=(
                    "Your ID request has been approved. "
                    "Click to view and print your official ID card."
                ),
                link=reverse("digital_id:officer_id", args=[officer.staffid])
            )

            messages.success(request, "ID request approved successfully.")

        # =====================================================
        # REJECTION FLOW
        # =====================================================
        elif action == "REJECTED":
            refund_result = payment.refund()
            if refund_result.get("status") == "success":
                messages.success(
                    request,
                    f"Payment refunded successfully to officer {officer.staffid}."
                )
            else:
                messages.error(
                    request,
                    f"Refund failed: {refund_result.get('message')}"
                )

            Notification.objects.create(
                user=officer,
                title="ID Request Rejected",
                message="Your ID request was rejected. Please contact support.",
            )

        return redirect(
            "admin_dash:admin_id_request_detail",
            staffid=officer.staffid
        )

    return render(
        request,
        "admin_dash/id_request_detail.html",
        {"approval": approval}
    )


# -----------------------------
# badge count in approvals
# -----------------------------

from django.http import JsonResponse
from digital_id.models import IDRequestApproval

def pending_requests_api(request):
    if request.user.is_staff or request.user.is_superuser:
        count = IDRequestApproval.objects.filter(status="PENDING").count()
        return JsonResponse({"count": count})
    return JsonResponse({"count": 0})


# -----------------------------
# bulk approve
# -----------------------------


from admin_dash.services import approve_id_request

@staff_member_required
def bulk_approve_requests(request):
    if request.method != "POST":
        return redirect("admin_dash:admin_id_request_list")

    ids = request.POST.getlist("request_ids")

    if not ids:
        messages.warning(request, "No requests selected.")
        return redirect("admin_dash:admin_id_request_list")

    approvals = (
        IDRequestApproval.objects
        .select_related(
            "id_request",
            "id_request__officer",
            "id_request__officer__profile",
        )
        .filter(id__in=ids, status="PENDING")
    )

    approved_count = 0

    for approval in approvals:
        if approve_id_request(approval, request.user):
            approved_count += 1

    messages.success(request, f"{approved_count} requests approved.")
    return redirect("admin_dash:admin_id_request_list")


# -----------------------------
# Officer submits lost/expired ID request
# -----------------------------
@login_required
def idrequest_form(request):
    # Ensure officer profile is complete
    if not request.user.profile_completed:
        messages.error(request, "You must complete your profile before requesting a new ID card.")
        return redirect("officers_dash:complete_profile")

    # Fetch pending requests only
    id_requests = IDRequest.objects.filter(
        officer=request.user,
        is_processed=False
    ).select_related("approval").order_by("-date_requested")

    has_pending_request = id_requests.filter(
        approval__status="PENDING"
    ).exists()

    if request.method == "POST":
        if has_pending_request:
            messages.warning(request, "You already have a pending request. Please wait for approval.")
            return redirect("officers_dash:dashboard")

        form = IDRequestForm(request.POST)
        if form.is_valid():
            id_request = form.save(commit=False)
            id_request.officer = request.user
            id_request.save()

            # Auto-create approval row
            IDRequestApproval.objects.create(id_request=id_request)

            # Deactivate QR immediately until admin approval
            profile = request.user.profile
            profile.is_active_qr = False
            profile.save(update_fields=["is_active_qr"])

            messages.success(request, "Your ID request has been submitted successfully. QR is temporarily deactivated until approval.")
            return redirect("officers_dash:dashboard")
    else:
        form = IDRequestForm()

    return render(request, "digital_id/idrequest_form.html", {
        "form": form,
        "has_pending_request": has_pending_request,
        "request_list": id_requests,
    })


# -----------------------------
# Admin approves/rejects request
# -----------------------------
@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)  # Admin only
def approve_request(request, approval_id):
    if request.method == "POST":
        approval = get_object_or_404(IDRequestApproval, id=approval_id)
        action = request.POST.get("action")

        if action not in ["APPROVED", "REJECTED"]:
            messages.error(request, "Invalid action.")
            return redirect("admin_dash:home")

        approval.status = action
        approval.approved_by = request.user
        approval.save(update_fields=["status", "approved_by"])

        # Process officer QR and notify
        profile = approval.id_request.officer.profile

        if action == "APPROVED":
            # Activate QR for 365 days
            profile.is_active_qr = True
            profile.qr_expiry_date = timezone.now() + timezone.timedelta(days=365)
            profile.save(update_fields=["is_active_qr", "qr_expiry_date"])

            # Mark request as processed
            approval.id_request.is_processed = True
            approval.id_request.save(update_fields=["is_processed"])

            # Send SMS with link to view/print ID card
            sms_result = send_qr_link(profile)
            if sms_result["success"]:
                messages.success(request, f"ID approved and SMS sent to {profile.user.get_full_name()}.")
            else:
                messages.warning(request, f"ID approved but SMS failed: {sms_result.get('error', 'Unknown error')}")

        elif action == "REJECTED":
            # Keep QR inactive
            profile.is_active_qr = False
            profile.save(update_fields=["is_active_qr"])

            # Mark request as processed
            approval.id_request.is_processed = True
            approval.id_request.save(update_fields=["is_processed"])
            messages.info(request, f"ID request rejected for {profile.user.get_full_name()}.")

    return redirect("admin_dash:home")




def staff_only(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(staff_only)
def user_search_ajax(request):
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"results": []})

    users = (
        User.objects.filter(
            Q(firstname__icontains=query) |
            Q(lastname__icontains=query) |
            Q(ghcard__icontains=query) |
            Q(staffid__icontains=query) |
            Q(service_number__icontains=query)
        )
        .distinct()
        .order_by("lastname")[:10]
    )

    return JsonResponse({
        "results": [
            {
                "staffid": u.staffid,
                "name": f"{u.firstname} {u.lastname}",
                "service_number": u.service_number or "—",
                "ghcard": u.ghcard or "—",
                "role": u.get_role_display(),
                "profile_url": reverse(
                    "admin_dash:admin_officer_detail",
                    args=[u.staffid]
                ),
            }
            for u in users
        ]
    })


@staff_member_required
def resend_qr(request, staffid):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("admin_dash:home")

    officer = get_object_or_404(User, staffid=staffid)
    profile = getattr(officer, "profile", None)

    if not profile:
        messages.error(request, "Officer profile not found.")
        return redirect("admin_dash:home")

    profile.is_active_qr = True
    profile.qr_token = uuid.uuid4().hex[:12].upper()
    profile.date_approved = timezone.now()

    profile._generate_qr_image()

    if not profile.qr_image:
        messages.error(request, "QR generation failed. Please try again.")
        return redirect("admin_dash:home")

    profile.save(update_fields=[
        "qr_image",
        "qr_token",
        "is_active_qr",
        "date_approved",
    ])

    result = send_qr_link(profile)

    if result.get("success") is True:
        Notification.objects.create(
            user=officer,
            title="QR Resent",
            message=f"Your QR code has been resent via {officer.get_preferred_qr_method_display()}."
        )
        messages.success(
            request,
            f"QR code resent successfully to {officer.get_full_name()} ({officer.staffid})."
        )
    else:
        messages.error(
            request,
            f"Failed to resend QR code: {result.get('error', 'Unknown error')}"
        )

    return redirect(request.META.get("HTTP_REFERER", "admin_dash:home"))
