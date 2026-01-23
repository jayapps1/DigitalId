
from django.core.management.base import BaseCommand
from digital_id.models import IDRequest
from payments.models import Payment

class Command(BaseCommand):
    help = "Delete IDRequests with missing or pending payments"

    def handle(self, *args, **options):
        all_requests = IDRequest.objects.all()
        ok_count = 0
        deleted_count = 0

        for req in all_requests:
            try:
                payment = req.payment  # Will raise RelatedObjectDoesNotExist if no payment
                if payment.status in ["PENDING", "FAILED"]:
                    self.stdout.write(f"Deleting IDRequest {req.id} with payment {payment.reference} status {payment.status}")
                    req.delete()
                    deleted_count += 1
                else:
                    ok_count += 1
            except IDRequest.payment.RelatedObjectDoesNotExist:
                self.stdout.write(f"Deleting IDRequest {req.id} with NO payment record")
                req.delete()
                deleted_count += 1

        self.stdout.write(f"Completed. OK: {ok_count}, Deleted: {deleted_count}")
