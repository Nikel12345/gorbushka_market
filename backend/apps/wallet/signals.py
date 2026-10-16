from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Wallet


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="wallet_create_for_user")
def create_wallet(sender, instance, created, raw=False, **kwargs):
    """Кошелёк появляется вместе с пользователем — любым путём: регистрация, админка, createsuperuser."""
    if created and not raw:
        Wallet.objects.get_or_create(user=instance)
