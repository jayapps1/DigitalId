from django.db import models
from django.utils import timezone
from django.conf import settings

class NFCCard(models.Model):
    profile = models.ForeignKey(
        'digital_id.OfficerProfile',
        on_delete=models.CASCADE,
        related_name='nfc_cards'
    )
    qr_token = models.CharField(
        max_length=12,
        editable=False,
        help_text="Links to OfficerProfile.qr_token"
    )
    is_active = models.BooleanField(default=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Always sync with OfficerProfile token
        if not self.qr_token:
            self.qr_token = self.profile.qr_token

        # Active only if officer's QR is valid
        self.is_active = self.profile.is_qr_valid()

        super().save(*args, **kwargs)

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.profile.user.staffid} NFC ({status})"


# -------------------------
# NFC SCAN LOG
# -------------------------
class NFCScanLog(models.Model):
    nfc_card = models.ForeignKey(
        NFCCard,
        on_delete=models.CASCADE,
        related_name='scan_logs'
    )
    scanned_at = models.DateTimeField(auto_now_add=True)
    device_id = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        ordering = ['-scanned_at']

    def __str__(self):
        return f"{self.nfc_card.profile.user.staffid} scanned at {self.scanned_at}"