from django.apps import AppConfig


class WalletConfig(AppConfig):
    name = "apps.wallet"
    verbose_name = "Баланс"

    def ready(self):
        from . import signals  # noqa: F401
