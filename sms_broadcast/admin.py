
# Register your models here.
from django.contrib import admin
from .models import SMSBroadcast, SMSDelivery


@admin.register(SMSBroadcast)
class SMSBroadcastAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender",
        "scope",
        "total_recipients",
        "sent_count",
        "delivered_count",
        "failed_count",
        "created_at",
    )
    list_filter = ("scope", "created_at")
    search_fields = ("message",)


@admin.register(SMSDelivery)
class SMSDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "broadcast",
        "user",
        "phone_number",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("phone_number", "provider_message_id")
