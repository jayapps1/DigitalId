from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),          # default Django admin
    path('', include(('digital_id.urls', 'digital_id'), namespace='digital_id')),  # login / public
    path('admin/', include('admin_dash.urls')),      # admin dashboard
    path('officer/', include(('officers_dash.urls', 'officers_dash'), namespace='officers_dash')),
    path("password-reset/", include("password_reset.urls", namespace="password_reset")),
    path("payments/", include("payments.urls", namespace="payments_sys")),
    path("momo_payments/", include("momo_payments.urls", namespace="momo_pay")),
 # officer dashboard
    path('id-card/', include('id_card.urls')),       # QR / ID card
    path('sms/', include('sms_broadcast.urls', namespace='sms_broadcast')),
    path('print-id/', include(('print_id.urls', 'print_id'), namespace='print_id')),
        # NFC Cards
    path('nfc/', include(('nfc_cards.urls', 'nfc_cards'), namespace='nfc_cards')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
