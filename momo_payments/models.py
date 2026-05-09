from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from digital_id.models import IDRequest
import logging

logger = logging.getLogger(__name__)


class MTNPayment(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    REQUEST_TYPES = (
        ("NEW", "New"),
        ("LOST", "Lost"),
        ("EXPIRED", "Expired"),
    )

    id_request = models.OneToOneField(
        IDRequest,
        on_delete=models.CASCADE,
        related_name="mtn_payment",
        null=True,
        blank=True
    )

    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )

    request_type = models.CharField(
        max_length=20,
        choices=REQUEST_TYPES,
        default="NEW"
    )

    phone_number = models.CharField(
        max_length=15,
        help_text="MSISDN format e.g. 233XXXXXXXXX"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=5,
        default="EUR"  # Sandbox; switch to GHS in live
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True
    )

    raw_response = models.JSONField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["id_request"],
                condition=Q(status="SUCCESS"),
                name="one_successful_mtn_payment_per_request"
            )
        ]

    def __str__(self):
        return f"MTN | {self.officer.staffid} | {self.reference} | {self.status}"

    # -----------------------------
    # Payment helpers (same pattern)
    # -----------------------------
    def mark_success(self, response_data=None):
        if self.status == "SUCCESS":
            return

        self.status = "SUCCESS"
        self.paid_at = timezone.now()
        self.raw_response = response_data
        self.save(update_fields=["status", "paid_at", "raw_response"])

        logger.info(f"MTN payment {self.reference} marked SUCCESS")

    def mark_failed(self, response_data=None):
        if self.status == "FAILED":
            return

        self.status = "FAILED"
        self.raw_response = response_data
        self.save(update_fields=["status", "raw_response"])

        logger.warning(f"MTN payment {self.reference} marked FAILED")
