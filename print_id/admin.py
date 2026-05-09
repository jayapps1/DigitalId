from django.contrib import admin
from .models import PrintRequest


@admin.register(PrintRequest)
class PrintRequestAdmin(admin.ModelAdmin):

    list_display = (
        "officer",
        "requested_by",
        "status",
        "requested_at",
        "approved_at",
        "printed_at",
        "locked_until",
    )

    list_filter = (
        "status",
        "requested_at",
        "approved_at",
        "printed_at",
        "locked_until",
    )

    search_fields = (
        "officer__user__first_name",
        "officer__user__last_name",
        "officer__user__staffid",
        "requested_by__first_name",
        "requested_by__last_name",
        "requested_by__staffid",
    )

    readonly_fields = (
        "requested_at",
        "approved_at",
        "printed_at",
        "locked_until",
    )

    actions = ["approve_selected_requests", "lock_selected_requests"]

    # Approve selected
    def approve_selected_requests(self, request, queryset):
        count = 0
        for pr in queryset:
            if pr.status == "PENDING":
                pr.approve(request.user)
                count += 1
        self.message_user(request, f"{count} requests approved.")
    approve_selected_requests.short_description = "Approve selected requests"

    # Lock selected
    def lock_selected_requests(self, request, queryset):
        updated = queryset.exclude(status="LOCKED").update(status="LOCKED")
        self.message_user(request, f"{updated} requests locked.")
    lock_selected_requests.short_description = "Lock selected requests"