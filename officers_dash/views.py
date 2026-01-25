from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.contrib import messages
from digital_id.models import OfficerProfile, IDRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404
from .forms import OfficerProfileForm, OfficerUserUpdateForm, OfficerSelfUpdateForm
from .decorators import profile_required
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.exceptions import NON_FIELD_ERRORS

from django.shortcuts import render

def qr_display(request, qr_token):
    """
    Display officer ID card (service_id_image) using a permanent QR token.
    - No login required for the SMS link.
    - Admin/superuser can view any card.
    - QR must be active and not expired.
    """

    profile = get_object_or_404(OfficerProfile, qr_token=qr_token)

    # -------------------------------------------------
    # 1. Superuser/admin bypass
    # -------------------------------------------------
    user = getattr(request, "user", None)
    if user and user.is_authenticated and (user.is_superuser or user.is_staff):
        return render(request, "officers_dash/qr_display.html", {"profile": profile})

    # -------------------------------------------------
    # 2. QR must be active and not expired
    # -------------------------------------------------
    if not profile.is_active_qr:
        return HttpResponseForbidden("This ID card is currently inactive. Please wait for approval.")

    if profile.qr_expiry_date and timezone.now() > profile.qr_expiry_date:
        return HttpResponseForbidden("This ID card link has expired.")

    # -------------------------------------------------
    # 3. Optional: ensure officer profile completed
    # -------------------------------------------------
    if profile.user.profile_completed is False:
        return HttpResponseForbidden("Officer profile incomplete. Cannot display ID card.")

    # -------------------------------------------------
    # 4. Render ID card for printing
    # -------------------------------------------------
    return render(request, "officers_dash/qr_display.html", {"profile": profile})




@login_required
def complete_profile(request):
    user = request.user

    # Ensure OfficerProfile exists
    profile, _ = OfficerProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        form = OfficerSelfUpdateForm(
            request.POST,
            request.FILES,
            instance=user,
            profile_instance=profile
        )

        try:
            if form.is_valid():
                form.save()
                messages.success(request, "Profile completed successfully.")
                return redirect("officers_dash:dashboard")

        except ValidationError as e:
            # Attach model validation errors to the form properly
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        if field in form.fields:
                            form.add_error(field, error)
                        else:
                            form.add_error(NON_FIELD_ERRORS, error)
            else:
                form.add_error(NON_FIELD_ERRORS, e.messages)

        # Keep this while stabilizing
        print("FORM ERRORS:", form.errors)

    else:
        form = OfficerSelfUpdateForm(
            instance=user,
            profile_instance=profile
        )

    return render(
        request,
        "officers_dash/complete_profile.html",
        {"user_form": form},
    )

@login_required
@profile_required
def dashboard(request):
    return render(request, "officers_dash/dashboard.html")



class OfficerDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "officers_dash/dashboard.html"

    def test_func(self):
        """Only allow superusers or officers with a profile."""
        user = self.request.user
        return user.is_superuser or OfficerProfile.objects.filter(user=user).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get officer profile
        profile = OfficerProfile.objects.filter(user=user).select_related("user").first()
        if not profile:
            messages.warning(self.request, "Your officer profile is incomplete.")
            return {
                "profile_missing": True,
                "profile": None,
                "id_requests": [],
                "has_pending_request": False,
            }

        # Fetch all ID requests
        id_requests = (
            IDRequest.objects
            .filter(officer=user)
            .select_related("approval")
            .order_by("-date_requested")
        )

        # Badge mapping for statuses
        badge_classes = {
            'PENDING': 'bg-warning text-dark',
            'APPROVED': 'bg-success',
            'REJECTED': 'bg-danger',
        }

        # Determine if any request is pending approval
        has_pending_request = id_requests.filter(
            Q(approval__status="PENDING") | Q(approval__isnull=True)
        ).exists()

        context.update({
            "profile": profile,
            "id_requests": id_requests,
            "badge_classes": badge_classes,
            "has_pending_request": has_pending_request
        })
        return context