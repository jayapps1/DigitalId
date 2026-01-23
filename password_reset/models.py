
# password_reset/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta
from digital_id.models import User  # your custom User



class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)

    def __str__(self):
        return f"OTP({self.user.staffid}) - {self.otp}"
