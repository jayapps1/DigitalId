from django.db import models
from django.conf import settings


# -------------------------
# SMS BROADCAST
# -------------------------
class SMSBroadcast(models.Model):
    SCOPE_CHOICES = (
        ("ALL", "All Users"),
        ("REGION", "Region"),
        ("STATION", "Station"),
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sms_broadcasts"
    )

    message = models.TextField()

    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES
    )

    # Optional filters; region comes from User, station comes from OfficerProfile
    region = models.CharField(max_length=20, blank=True, null=True)
    station = models.CharField(max_length=255, blank=True, null=True)

    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"SMS #{self.id} - {self.scope} - {self.created_at.date()}"


# -------------------------
# SMS DELIVERY TRACKING
# -------------------------
class SMSDelivery(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SENT", "Sent to Gateway"),
        ("DELIVERED", "Delivered"),
        ("FAILED", "Failed"),
    )

    broadcast = models.ForeignKey(
        SMSBroadcast,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sms_deliveries"
    )

    # Store the exact phone used for sending at the time of broadcast
    phone_number = models.CharField(max_length=20)

    # Optional provider message ID from SMS gateway
    provider_message_id = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    response_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)

    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("broadcast", "user")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["provider_message_id"]),
        ]

    def __str__(self):
        return f"{self.user.staffid} - {self.status}"
