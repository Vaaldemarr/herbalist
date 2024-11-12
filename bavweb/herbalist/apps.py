from django.apps import AppConfig


class HerbalistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'herbalist'

    def ready(self):
        import herbalist.signals
