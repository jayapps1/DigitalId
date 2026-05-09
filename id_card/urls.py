from django.urls import path
from . import views

app_name = "id_card"

urlpatterns = [
    path("verify/<str:token>/", views.verify_id, name="verify"),
    path('update_gps/', views.update_gps, name='update_gps'),
    path('scan_logs/', views.scan_logs, name='scan_logs'),           # list of all scans
    path('scan/<int:scan_id>/', views.scan_detail, name='scan_detail'),  # view single scan on map

]
