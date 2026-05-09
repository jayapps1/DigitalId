from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.urls import reverse
from digital_id.models import OfficerProfile, Notification


class PrintRequest(models.Model):

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('PRINTED', 'Printed'),
        ('LOCKED', 'Locked'),
        ('REJECTED', 'Rejected'),
    ]

    officer = models.ForeignKey(
        OfficerProfile,
        on_delete=models.CASCADE,
        related_name="print_requests"
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="print_requests_made"
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')

    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    printed_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"{self.officer.user.get_full_name()} - {self.status}"

    # -------------------------
    # BUSINESS LOGIC
    # -------------------------

    def can_officer_request(self):
        """Check if officer is eligible to request print"""
        # Payment check
        if not getattr(self.officer, "payment_successful", False):
            return False

        # QR expiry
        if self.officer.qr_expiry_date and self.officer.qr_expiry_date < timezone.now().date():
            return False

        # Pending request check
        if PrintRequest.objects.filter(officer=self.officer, status='PENDING').exists():
            return False

        # Active printed lock
        if PrintRequest.objects.filter(
            officer=self.officer,
            status='PRINTED',
            locked_until__gte=timezone.now()
        ).exists():
            return False

        return True

    @property
    def is_printable(self):
        return self.status == 'APPROVED'

    # -------------------------
    # NOTIFICATIONS
    # -------------------------
    def notify_admins(self):
        """Notify all Region Admins & Superadmins via in-app notifications"""
        from django.contrib.auth import get_user_model
        User = get_user_model()

        admins = User.objects.filter(role__in=['REGIONAL_ADMIN', 'SUPERADMIN'], is_active=True)
        for admin in admins:
            # URL to admin view of this print request
            link = reverse('admin_print_request_detail', args=[self.id])
            Notification.objects.create(
                user=admin,
                title=f"Print Request for {self.officer.user.get_full_name()}",
                message=f"Officer {self.officer.user.get_full_name()} has requested a print of their ID. Approve or print here.",
                link=link
            )

    # -------------------------
    # APPROVE / REJECT
    # -------------------------
    def approve(self, admin_user):
        if self.status != 'PENDING':
            raise ValueError("Only pending requests can be approved.")
        if not admin_user.role in ['REGIONAL_ADMIN', 'SUPERADMIN']:
            raise PermissionError("Only eligible admins can approve.")

        self.status = 'APPROVED'
        self.approved_at = timezone.now()
        self.save(update_fields=['status', 'approved_at'])
        self.notify_officer_approved()

    def reject(self, admin_user, reason=None):
        if self.status != 'PENDING':
            raise ValueError("Only pending requests can be rejected.")
        if not admin_user.role in ['REGIONAL_ADMIN', 'SUPERADMIN']:
            raise PermissionError("Only eligible admins can reject.")

        self.status = 'REJECTED'
        self.save(update_fields=['status'])
        self.notify_officer_rejected(reason)

    # -------------------------
    # MARK PRINTED
    # -------------------------
    def mark_printed(self, admin_user):
        if self.status != 'APPROVED':
            raise ValueError("Only approved requests can be marked printed.")
        if not admin_user.role in ['REGIONAL_ADMIN', 'SUPERADMIN']:
            raise PermissionError("Only eligible admins can mark printed.")

        self.status = 'PRINTED'
        self.printed_at = timezone.now()
        self.locked_until = timezone.now() + timedelta(weeks=2)
        self.save(update_fields=['status', 'printed_at', 'locked_until'])
        self.notify_officer_printed()

    # -------------------------
    # LOCK IF EXPIRED
    # -------------------------
    def lock_if_expired(self):
        if self.status == 'PRINTED' and self.locked_until and timezone.now() > self.locked_until:
            self.status = 'LOCKED'
            self.save(update_fields=['status'])

    # -------------------------
    # OFFICER NOTIFICATIONS
    # -------------------------
    def notify_officer_approved(self):
        link = reverse('officer_print_view', args=[self.id])
        Notification.objects.create(
            user=self.officer.user,
            title="Print Request Approved",
            message=f"Your print request has been approved. You can view it here.",
            link=link
        )

    def notify_officer_rejected(self, reason=None):
        msg = "Your print request has been rejected."
        if reason:
            msg += f" Reason: {reason}"
        Notification.objects.create(
            user=self.officer.user,
            title="Print Request Rejected",
            message=msg
        )

    def notify_officer_printed(self):
        Notification.objects.create(
            user=self.officer.user,
            title="Print Completed",
            message="Your ID has been successfully printed. The print link is now inactive."
        )