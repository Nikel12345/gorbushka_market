from django.apps import AppConfig


class PromoConfig(AppConfig):
    name = "apps.promo"
    verbose_name = "Реклама"

    def ready(self):
        from . import signals  # noqa: F401
