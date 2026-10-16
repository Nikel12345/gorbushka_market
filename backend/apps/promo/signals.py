from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.files import delete_file_on_commit

from .models import Promo


@receiver(post_delete, sender=Promo)
def delete_promo_files(sender, instance, **kwargs):
    delete_file_on_commit(instance.image)
    delete_file_on_commit(instance.image_mobile)
