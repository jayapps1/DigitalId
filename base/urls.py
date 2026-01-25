from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from admin_dash.views import pending_requests_api

urlpatterns = [
    path('django-admin/', admin.site.urls),          # default Django admin
    path('', include(('digital_id.urls', 'digital_id'), namespace='digital_id')),  # login / public
    path('admin/', include('admin_dash.urls')),      # admin dashboard
    path('officer/', include(('officers_dash.urls', 'officers_dash'), namespace='officers_dash')),
    path("password-reset/", include("password_reset.urls", namespace="password_reset")),
    path("payments/", include("payments.urls", namespace="payments_sys")),
 # officer dashboard
    path('id-card/', include('id_card.urls')),       # QR / ID card
        # API endpoint for pending requests badge
    path("api/pending-requests-count/", pending_requests_api, name="pending_requests_api"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
