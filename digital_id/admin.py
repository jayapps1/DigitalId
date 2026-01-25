from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.utils.html import format_html
import logging
from django.urls import path, reverse
from django.shortcuts import redirect, get_object_or_404
from digital_id.models import IDRequest, IDRequestApproval

logger = logging.getLogger(__name__)



from .models import (
    User,
    OfficerProfile,
    Notification,
    IDRequest,
    IDRequestApproval,
    QRScanLog,
)

# =========================
# USER ADMIN
# =========================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    list_display = (
        "staffid",
        "firstname",
        "lastname",
        "service_number",
        "ghcard",
        "region",
        "role",
        "is_active",
    )

    list_filter = ("role", "region", "is_active")
    search_fields = ("staffid", "firstname", "lastname", "service_number", "ghcard")
    ordering = ("staffid",)

    fieldsets = (
        ("Login Credentials", {
            "fields": ("staffid", "password")
        }),
        ("Personal Information", {
            "fields": (
                "firstname",
                "lastname",
                "gender",
                "service_number",
                "ghcard",
            )
        }),
        ("Contact", {
            "fields": ("phone", "email", "region", "district")
        }),
        ("Permissions", {
            "fields": (
                "role",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Security", {
            "fields": ("must_change_password",)
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "staffid",
                "firstname",
                "lastname",
                "gender",
                "service_number",
                "password1",
                "password2",
                "role",
                "is_staff",
            ),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change and not obj.password:
            obj.password = make_password("Officer@123")
            if obj.is_officer:
                obj.must_change_password = True
        super().save_model(request, obj, form, change)



# =========================
# OFFICER PROFILE ADMIN
# =========================
@admin.register(OfficerProfile)
class OfficerProfileAdmin(admin.ModelAdmin):

    # -------------------------
    # LIST VIEW
    # -------------------------
    list_display = (
        "user",
        "rank",
        "blood_group",
        "station",
        "leave_type",
        "called_off",
        "has_service_id",
        "is_active_qr",
    )

    list_filter = (
        "rank",
        "blood_group",
        "leave_type",
        "is_active_qr",
    )

    search_fields = (
        "user__staffid",
        "user__firstname",
        "user__lastname",
    )

    # -------------------------
    # READONLY FIELDS
    # -------------------------
    readonly_fields = (
        "service_id_preview",
    )

    # -------------------------
    # FORM LAYOUT
    # -------------------------
    fieldsets = (
        ("Officer Information", {
            "fields": (
                "user",
                "photo",
                "rank",
                "blood_group",
                "station",
            )
        }),

        ("Leave Management", {
            "fields": (
                "leave_type",
                "leave_start",
                "leave_end",
                "called_off",
            )
        }),

        ("QR & Service ID", {
            "fields": (
                "qr_image",
                "service_id_preview",
                "is_active_qr",
                "qr_expiry_date",
                "date_approved",
            )
        }),
    )

    # -------------------------
    # BOOLEAN: SERVICE ID EXISTS
    # -------------------------
    def has_service_id(self, obj):
        return bool(obj.service_id_image)

    has_service_id.boolean = True
    has_service_id.short_description = "Service ID"

    # -------------------------
    # SERVICE ID PREVIEW
    # -------------------------
    def service_id_preview(self, obj):
        if obj.service_id_image:
            return format_html(
                '<img src="{}" width="280" style="border:1px solid #ccc; border-radius:6px;" />',
                obj.service_id_image.url
            )
        return "—"

    service_id_preview.short_description = "Service ID Preview"

    # -------------------------
    # ADMIN ACTION
    # -------------------------
    @admin.action(description="Regenerate Service ID")
    def regenerate_service_id(self, request, queryset):
        for profile in queryset:
            if profile.photo:
                profile._generate_service_id_image()
                profile.date_approved = timezone.now()
                profile.save()

    actions = ["regenerate_service_id"]





@admin.register(IDRequest)
class IDRequestAdmin(admin.ModelAdmin):
    list_display = (
        "officer",
        "request_type",
        "date_requested",
        "approval_status",
        "refund_status_display",
        "refund_actions",  # <-- Button column
    )
    list_filter = (
        "request_type",
        "date_requested",
        "payment__refund_status",
    )
    search_fields = (
        "officer__staffid",
        "officer__firstname",
        "officer__lastname",
    )
    ordering = ("-date_requested",)

    actions = ["reject_request", "retry_failed_refunds"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            "officer",
            "payment",
            "approval",
        ).filter(payment__status="SUCCESS")

    @admin.display(description="Approval Status")
    def approval_status(self, obj):
        if hasattr(obj, "approval") and obj.approval:
            return obj.approval.status
        return "PENDING"

    @admin.display(description="Refund Status")
    def refund_status_display(self, obj):
        payment = getattr(obj, "payment", None)
        return payment.refund_status if payment else "NO PAYMENT"

    @admin.display(description="Actions")
    def refund_actions(self, obj):
        payment = getattr(obj, "payment", None)
        if payment and payment.refund_status == "FAILED":
            url = reverse('admin:digital_id_idrequest_retry_refund', args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="padding:2px 6px; background-color:#f44336; color:white; border-radius:3px;">Retry Refund</a>',
                url
            )
        return "-"

    # ----------------------------
    # Admin Action: Reject Request
    # ----------------------------
    def reject_request(self, request, queryset):
        for id_request in queryset:
            payment = getattr(id_request, "payment", None)
            if payment and payment.status == "SUCCESS":
                refund_result = payment.refund(initiated_by=request.user)
                if refund_result["status"] == "success":
                    messages.success(
                        request,
                        f"Refund SUCCESS for request {id_request.id} (Payment {payment.reference})"
                    )
                else:
                    messages.error(
                        request,
                        f"Refund FAILED for request {id_request.id} (Payment {payment.reference}): {refund_result['message']}"
                    )
                logger.info(f"Admin {request.user} rejected IDRequest {id_request.id}, refund result: {refund_result}")

            # Update or create Approval
            if hasattr(id_request, "approval") and id_request.approval:
                id_request.approval.status = "REJECTED"
                id_request.approval.save(update_fields=["status"])
            else:
                IDRequestApproval.objects.create(
                    id_request=id_request,
                    status="REJECTED",
                    approved_by=request.user,
                    date_processed=timezone.now()
                )
                logger.info(f"Approval record auto-created for rejected IDRequest {id_request.id}")

        self.message_user(request, "Selected requests have been rejected.")

    reject_request.short_description = "Reject selected ID requests"

    # ----------------------------
    # Admin Action: Retry Failed Refunds
    # ----------------------------
    def retry_failed_refunds(self, request, queryset):
        for id_request in queryset:
            payment = getattr(id_request, "payment", None)
            if not payment:
                messages.warning(request, f"No payment found for request {id_request.id}")
                continue

            if payment.refund_status != "FAILED":
                messages.info(
                    request,
                    f"Payment {payment.reference} refund not failed (current status: {payment.refund_status})"
                )
                continue

            # Retry refund
            refund_result = payment.refund(initiated_by=request.user)
            if refund_result["status"] == "success":
                messages.success(
                    request,
                    f"Refund RETRY SUCCESS for request {id_request.id} (Payment {payment.reference})"
                )
            else:
                messages.error(
                    request,
                    f"Refund RETRY FAILED for request {id_request.id} (Payment {payment.reference}): {refund_result['message']}"
                )
            logger.info(f"Admin {request.user} retried refund for IDRequest {id_request.id}, result: {refund_result}")

        self.message_user(request, "Retry refund process completed.")

    retry_failed_refunds.short_description = "Retry failed refunds for selected requests"

    # ----------------------------
    # Custom admin URL for per-row retry button
    # ----------------------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/retry-refund/',
                self.admin_site.admin_view(self.retry_refund_view),
                name='digital_id_idrequest_retry_refund',
            ),
        ]
        return custom_urls + urls

    def retry_refund_view(self, request, pk):
        id_request = get_object_or_404(IDRequest, pk=pk)
        payment = getattr(id_request, "payment", None)

        if not payment:
            messages.error(request, "No payment associated with this request.")
            return redirect(request.META.get('HTTP_REFERER', '..'))

        if payment.refund_status != "FAILED":
            messages.info(request, f"Refund not failed (status: {payment.refund_status}).")
            return redirect(request.META.get('HTTP_REFERER', '..'))

        refund_result = payment.refund(initiated_by=request.user)
        if refund_result["status"] == "success":
            messages.success(request, f"Refund RETRY SUCCESS for {id_request.id}")
        else:
            messages.error(request, f"Refund RETRY FAILED for {id_request.id}: {refund_result['message']}")

        return redirect(request.META.get('HTTP_REFERER', '..'))

# =========================
# ID REQUEST APPROVAL ADMIN
# =========================
@admin.register(IDRequestApproval)
class IDRequestApprovalAdmin(admin.ModelAdmin):
    list_display = ("id_request", "status", "approved_by", "date_processed")
    list_filter = ("status", "id_request__request_type")
    search_fields = ("id_request__officer__staffid",)

    actions = ["approve_requests"]

    @admin.action(description="Approve selected requests")
    def approve_requests(self, request, queryset):
        for approval in queryset:
            if approval.status != "APPROVED":
                approval.status = "APPROVED"
                approval.approved_by = request.user
                approval.date_processed = timezone.now()
                approval.save(update_fields=["status", "approved_by", "date_processed"])



# =========================
# NOTIFICATION ADMIN
# =========================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("user__staffid", "title")


# =========================
# QR SCAN LOG ADMIN
# =========================
@admin.register(QRScanLog)
class QRScanLogAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "scanned_at",
        "phone_number",
        "email",
        "ip_address",
    )
    search_fields = ("profile__user__staffid", "phone_number", "email")
    list_filter = ("scanned_at",)
