# admin_dash/urls.py
from django.urls import path
from admin_dash.views import (
    AdminHomeView,
    RegenerateQRView,
    admin_print_qr,  # Import the function-based view
    AdminOfficerDetailView,
    AdminOfficerEditView,
    AdminOfficerDeleteView
    
)
from . import views

app_name = "admin_dash"

urlpatterns = [
    path("admin-dash/", AdminHomeView.as_view(), name="home"),
    path("admin/qr/regenerate/<str:staffid>/", RegenerateQRView.as_view(), name="qr_regenerate"),
    path("print-qr/<str:staffid>/", admin_print_qr, name="admin_print_qr"),  # Fixed

    # Optional: add officer CRUD URLs
    path("officer/<str:staffid>/", AdminOfficerDetailView.as_view(), name="admin_officer_detail"),
    path("officer/<str:staffid>/edit/", AdminOfficerEditView.as_view(), name="admin_officer_edit"),
    path("officer/<str:staffid>/delete/", AdminOfficerDeleteView.as_view(), name="admin_officer_delete"),
    path('api/pending-requests-count/', views.pending_requests_api, name='pending_requests_api'),
    path('bulk-approve-requests/', views.bulk_approve_requests, name='bulk_approve_requests'),
    path("admin/id-requests/", views.admin_id_request_list, name="admin_id_request_list" ),
    path( "admin/id-requests/staff/<str:staffid>/", views.admin_id_request_detail, name="admin_id_request_detail"),
    path('id-requests/approve/<int:approval_id>/', views.approve_request, name='approve_request'),
    path("search/ajax/", views.user_search_ajax, name="user_search_ajax"),
    path('resend-qr/<str:staffid>/', views.resend_qr, name='resend_qr'),

]
