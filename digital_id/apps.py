from django.apps import AppConfig

class DigitalIdConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'digital_id'

    def ready(self):
        import digital_id.signals
