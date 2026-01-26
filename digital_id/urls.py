from django.urls import path
from .views import Home, user_login, user_logout, change_password
from . import views
from digital_id.views import request_id_view
from digital_id.views import OfficerExcelImportView
from digital_id.views import NotificationsView
app_name = 'digital_id'  # for namespacing

urlpatterns = [
    path('', Home, name='home'),                       # Landing / Home page
    path('login/', user_login, name='login'),          # Login page
    path('logout/', user_logout, name='logout'),       # Logout
    path('change-password/', change_password, name='change_password'),  # Password change for officers
    path("id-request/", request_id_view, name="request_id"),
     path('import-officer/', OfficerExcelImportView.as_view(), name='import_officer'),
    path("admin/register-officer/", views.register_officer, name="register_officer"),
    path('officer/<str:staffid>/print-id/', views.officer_id, name='officer_id'),   
    path('notifications/', NotificationsView.as_view(), name='notifications'),
     path("notifications/view/<int:pk>/", views.view_notification, name="view_notification"),
    path("notifications/delete/<int:pk>/", views.delete_notification, name="delete_notification"),
    path("notifications/bulk-delete/", views.bulk_delete_notifications, name="bulk_delete_notifications"),
    path('notifications/ajax/mark-as-read/<int:pk>/', views.mark_as_read, name='ajax_mark_as_read'),
    path('notifications/ajax/unread-count/', views.get_unread_count, name='ajax_unread_count'),
    path('about/', views.about, name='about'),
    

    
]
     

