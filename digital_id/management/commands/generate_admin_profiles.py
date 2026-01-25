# digital_id/management/commands/generate_admin_profiles.py
from django.core.management.base import BaseCommand
from digital_id.models import User, OfficerProfile

class Command(BaseCommand):
    help = "Ensure all ADMIN and SUPERADMIN users have OfficerProfiles with QR and service ID images"

    def handle(self, *args, **kwargs):
        admins = User.objects.filter(role__in=["ADMIN", "SUPERADMIN"])
        processed_count = 0

        for admin in admins:
            profile, created = OfficerProfile.objects.get_or_create(user=admin)

            # Regenerate QR image if missing
            if not profile.qr_image:
                profile._generate_qr_image()

            # Regenerate service ID image if missing
            if not profile.service_id_image:
                profile._generate_service_id_image()

            # Save updated profile
            profile.save(update_fields=["qr_image", "service_id_image"])
            processed_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"{'Created' if created else 'Updated'} profile for {admin.staffid}"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"Done. Profiles processed: {processed_count}"))
