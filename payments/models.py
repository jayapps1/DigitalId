from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from digital_id.models import IDRequest
import logging
import requests

logger = logging.getLogger(__name__)

class Payment(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    REFUND_STATUS_CHOICES = (
        ("NONE", "No Refund"),
        ("PENDING", "Refund Pending"),
        ("SUCCESS", "Refunded"),
        ("FAILED", "Refund Failed"),
    )

    REQUEST_TYPES = (
        ("NEW", "New"),
        ("LOST", "Lost"),
        ("EXPIRED", "Expired"),
    )

    id_request = models.OneToOneField(
        IDRequest,
        on_delete=models.CASCADE,
        related_name="payment",
        null=True,
        blank=True
    )
    officer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    reference = models.CharField(max_length=100, unique=True)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES, default="NEW")

    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2)
    paystack_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)

    refund_status = models.CharField(max_length=20, choices=REFUND_STATUS_CHOICES, default="NONE")
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_response = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["id_request"],
                condition=Q(status="SUCCESS"),
                name="one_successful_payment_per_request"
            )
        ]

    def __str__(self):
        return f"{self.officer.staffid} | {self.request_type} | {self.status}"

    # -----------------------------
    # Payment helpers
    # -----------------------------
    def mark_success(self, response_data=None):
        if self.status == "SUCCESS":
            return
        self.status = "SUCCESS"
        self.paid_at = timezone.now()
        self.raw_response = response_data
        self.save(update_fields=["status", "paid_at", "raw_response"])
        logger.info(f"Payment {self.reference} marked SUCCESS")

    def mark_failed(self, response_data=None):
        if self.status == "FAILED":
            return
        self.status = "FAILED"
        self.raw_response = response_data
        self.save(update_fields=["status", "raw_response"])
        logger.warning(f"Payment {self.reference} marked FAILED")

    # -----------------------------
    # Refund helpers
    # -----------------------------
    def mark_refund_pending(self, response_data=None):
        if self.refund_status != "NONE":
            return
        self.refund_status = "PENDING"
        self.refund_response = response_data
        self.save(update_fields=["refund_status", "refund_response"])
        logger.info(f"Refund initiated for {self.reference}")

    def mark_refund_success(self, response_data=None):
        if self.refund_status == "SUCCESS":
            return
        self.refund_status = "SUCCESS"
        self.refunded_at = timezone.now()
        self.refund_response = response_data
        self.save(update_fields=["refund_status", "refunded_at", "refund_response"])
        logger.info(f"Refund SUCCESS for {self.reference}")

    def mark_refund_failed(self, response_data=None):
        self.refund_status = "FAILED"
        self.refund_response = response_data
        self.save(update_fields=["refund_status", "refund_response"])
        logger.error(f"Refund FAILED for {self.reference}")

    # -----------------------------
    # Centralized refund method
    # -----------------------------
    def refund(self, initiated_by=None):
        """
        Initiates a refund via Paystack.
        Works in sandbox (DEBUG) mode automatically.
        Updates refund_status and logs automatically.
        Returns dict: {'status', 'message', 'data'}
        """
        if self.status != "SUCCESS":
            logger.warning(f"Cannot refund payment {self.reference}: not successful")
            return {"status": "failed", "message": "Payment not successful", "data": None}

        if self.refund_status in ["PENDING", "SUCCESS"]:
            logger.warning(f"Refund already processed for {self.reference}")
            return {"status": "failed", "message": "Refund already processed", "data": None}

        # Sandbox mode: simulate refund
        if settings.DEBUG:
            self.mark_refund_success({"message": "Sandbox refund simulated"})
            logger.info(f"Sandbox refund simulated for {self.reference} by {initiated_by}")
            return {"status": "success", "message": "Sandbox refund simulated", "data": {}}

        # Mark as pending before calling API
        self.mark_refund_pending()

        url = "https://api.paystack.co/refund"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"reference": self.reference}

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Paystack refund response for {self.reference}: {data}")

            if data.get("status"):
                self.mark_refund_success(data)
                logger.info(f"Refund for {self.reference} initiated by {initiated_by}")
                return {
                    "status": "success",
                    "message": data.get("message", "Refund successful"),
                    "data": data.get("data", {}),
                }
            else:
                self.mark_refund_failed(data)
                return {
                    "status": "failed",
                    "message": data.get("message", "Refund failed"),
                    "data": data,
                }

        except requests.RequestException as e:
            logger.error(f"HTTP error during refund for {self.reference}: {str(e)}", exc_info=True)
            self.mark_refund_failed({"error": str(e)})
            return {"status": "failed", "message": str(e), "data": None}
        except Exception as e:
            logger.exception(f"Unexpected error during refund for {self.reference}")
            self.mark_refund_failed({"error": str(e)})
            return {"status": "failed", "message": str(e), "data": None}
