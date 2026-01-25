from django.urls import path
from .views import OfficerDashboardView
from . import views
from admin_dash.views import AdminOfficerDetailView

app_name = "officers_dash"

urlpatterns = [
    path("officer-dash/", OfficerDashboardView.as_view(), name="dashboard"),
    path("complete-profile/", views.complete_profile, name="complete_profile"),
    path('id-card/verify/<str:qr_token>/', views.qr_display, name="qr_display"),
    path( "profile/<str:staffid>/",AdminOfficerDetailView.as_view(), name="officer_detail"),

]

