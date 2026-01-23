from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    # -----------------------------
    # LIST VIEW
    # -----------------------------
    list_display = (
        "reference",
        "officer",
        "request_type",
        "status",
        "refund_status",
        "total_amount",
        "paid_at",
        "refunded_at",
        "created_at",
    )

    list_filter = (
        "status",
        "refund_status",
        "request_type",
        "created_at",
    )

    search_fields = (
        "reference",
        "officer__staffid",
        "officer__first_name",
        "officer__last_name",
        "officer__email",
    )

    ordering = ("-created_at",)

    # -----------------------------
    # READ-ONLY FIELDS (CRITICAL)
    # -----------------------------
    readonly_fields = (
        "reference",
        "officer",
        "id_request",
        "request_type",
        "base_amount",
        "service_fee",
        "paystack_fee",
        "total_amount",
        "status",
        "paid_at",
        "raw_response",
        "refund_status",
        "refunded_at",
        "refund_response",
        "created_at",
    )

    # -----------------------------
    # FIELD GROUPING
    # -----------------------------
    fieldsets = (
        ("Payment Identification", {
            "fields": (
                "reference",
                "officer",
                "id_request",
                "request_type",
            )
        }),

        ("Amounts", {
            "fields": (
                "base_amount",
                "service_fee",
                "paystack_fee",
                "total_amount",
            )
        }),

        ("Payment Status", {
            "fields": (
                "status",
                "paid_at",
                "raw_response",
            )
        }),

        ("Refund Status", {
            "fields": (
                "refund_status",
                "refunded_at",
                "refund_response",
            )
        }),

        ("System Metadata", {
            "fields": (
                "created_at",
            )
        }),
    )

    # -----------------------------
    # ADMIN SAFETY OVERRIDES
    # -----------------------------
    def has_add_permission(self, request):
        """
        Payments must NEVER be created manually.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Payments must NEVER be deleted.
        """
        return False

    def save_model(self, request, obj, form, change):
        """
        Prevent admins from altering payment records.
        """
        if change:
            self.message_user(
                request,
                "Payments cannot be edited manually. "
                "All updates must come from Paystack or system logic.",
                level="ERROR",
            )
            return
        super().save_model(request, obj, form, change)
