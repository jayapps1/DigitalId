from django.contrib import admin
from .models import MTNPayment


@admin.register(MTNPayment)
class MTNPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "officer",
        "phone_number",
        "amount",
        "currency",
        "status",
        "created_at",
        "paid_at",
    )

    list_filter = (
        "status",
        "currency",
        "request_type",
        "created_at",
    )

    search_fields = (
        "reference",
        "phone_number",
        "officer__username",
        "officer__staffid",
    )

    readonly_fields = (
        "reference",
        "status",
        "paid_at",
        "raw_response",
        "created_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        ("Payment Reference", {
            "fields": ("reference", "status")
        }),
        ("Officer / Request", {
            "fields": ("officer", "id_request", "request_type")
        }),
        ("MoMo Details", {
            "fields": ("phone_number", "amount", "currency")
        }),
        ("System Timestamps", {
            "fields": ("created_at", "paid_at")
        }),
        ("Raw MTN Response (Debug)", {
            "classes": ("collapse",),
            "fields": ("raw_response",)
        }),
    )
