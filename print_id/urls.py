from django.urls import path
from . import views

app_name = "print_id"

urlpatterns = [

    # Officer
    path("my-requests/", views.officer_print_requests, name="officer_requests"),
    path("request-print/", views.request_print_card, name="request_print"),

    # Admin
    path("admin/requests/", views.admin_print_requests, name="admin_requests"),
    path("admin/approve/<int:request_id>/", views.approve_print_request, name="approve_request"),
    path("admin/print/<int:request_id>/", views.print_officer_card, name="print_officer_card"),
]