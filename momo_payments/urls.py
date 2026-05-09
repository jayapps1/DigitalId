from django.urls import path
from . import views



app_name = 'momo_pay'  # for namespacing

urlpatterns = [
    path("start/<int:id_request_id>/", views.start_mtn_payment, name="start_mtn_payment"),
    path("status/<str:reference>/", views.mtn_payment_status, name="mtn_payment_status"),
]
