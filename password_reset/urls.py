# password_reset/urls.py
from django.urls import path
from . import views

app_name = "password_reset"

urlpatterns = [
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("set-new-password/", views.set_new_password, name="set_new_password"),
    path("resend-otp/", views.resend_otp, name="resend_otp"),
]
