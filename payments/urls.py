from django.urls import path
from . import views



app_name = 'payments_sys'  # for namespacing

urlpatterns = [
    path("start/<str:request_type>/", views.start_new_id_payment, name="start_new_id_payment"),
    path("resume-payment/<str:staffid>/", views.resume_payment_view, name="resume_payment"),
    path("resume-pay/<int:payment_id>/", views.resume_payment_paystack, name="resume_payment_paystack"),  # new
    path("webhook/", views.paystack_webhook, name="webhook"),
    path("verify/", views.verify_payment, name="verify_payment"),
]
