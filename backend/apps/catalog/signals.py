from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.core.files import delete_file_on_commit

from .models import ProductImage


@receiver(post_delete, sender=ProductImage)
def delete_image_file(sender, instance, **kwargs):
    """Срабатывает при любом удалении — через сервис, в админке, каскадом с товаром."""
    delete_file_on_commit(instance.image)
