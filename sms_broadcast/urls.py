# sms_broadcast/urls.py
from django.urls import path
from . import views

app_name = "sms_broadcast"

urlpatterns = [
    path("send_sms/", views.send_broadcast, name="send_sms"),
]
