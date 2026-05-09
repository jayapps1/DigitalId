from django.urls import path
from . import views

app_name = "nfc_cards"

urlpatterns = [
    # NFC vCard download by token
    path('vcard/<str:token>/', views.nfc_vcard, name='nfc_vcard'),

    # Optional: scan logs view
    path('scan-logs/', views.nfc_scan_logs, name='scan_logs'),
    path('scan-logs/<str:staffid>/', views.nfc_scan_logs, name='scan_logs_officer'),
]