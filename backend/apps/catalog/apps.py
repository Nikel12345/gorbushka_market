from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = "apps.catalog"
    verbose_name = "Каталог"

    def ready(self):
        from . import signals  # noqa: F401
