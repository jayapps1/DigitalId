from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from digital_id.models import OfficerProfile
from nfc_cards.models import NFCCard

# -------------------------
# NFCCard Admin
# -------------------------
@admin.register(NFCCard)
class NFCCardAdmin(admin.ModelAdmin):
    list_display = ('profile', 'qr_token', 'is_active', 'issued_at')
    list_filter = ('is_active', 'issued_at')
    search_fields = ('profile__user__staffid', 'qr_token')
    readonly_fields = ('qr_token', 'issued_at')
    ordering = ('-issued_at',)

# -------------------------
# Optional: Inline on OfficerProfile
# -------------------------
class NFCCardInline(admin.TabularInline):
    model = NFCCard
    extra = 0
    readonly_fields = ('qr_token', 'issued_at')
    fields = ('qr_token', 'is_active', 'issued_at')

# -------------------------
# OfficerProfile Admin with safety check
# -------------------------
class OfficerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rank', 'station', 'blood_group', 'leave_type')
    inlines = [NFCCardInline]
    search_fields = ('user__staffid', 'user__firstname', 'user__lastname')
    list_filter = ('rank', 'station', 'blood_group', 'leave_type')

# Register only if not already registered
try:
    admin.site.register(OfficerProfile, OfficerProfileAdmin)
except AlreadyRegistered:
    pass