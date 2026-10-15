from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ShopQuerySet(models.QuerySet):
    def managed_by(self, user):
        """
        Магазины, которыми пользователь может управлять из кабинета продавца.
        Единственная точка проверки доступа к магазину: когда появятся сотрудники
        и роли, меняется только этот метод.
        """
        if not user.is_authenticated:
            return self.none()
        return self.filter(owner=user)

    def public(self):
        """
        Магазины, видимые покупателям. Сейчас — все; сюда добавится модерация,
        блокировка, «магазин закрыт» и т.п.
        """
        return self.all()

    def with_stats(self):
        """Счётчики для страниц магазина. Новые агрегаты добавляются здесь."""
        from apps.catalog.models import Product

        return self.annotate(
            products_count=models.Count(
                "products",
                filter=models.Q(products__status=Product.Status.ACTIVE),
            ),
        )


class Shop(TimeStampedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shops",
        verbose_name="владелец",
    )
    name = models.CharField("название", max_length=255)
    description = models.TextField("описание", blank=True)

    objects = ShopQuerySet.as_manager()

    class Meta:
        verbose_name = "магазин"
        verbose_name_plural = "магазины"
        ordering = ["id"]

    def __str__(self):
        return self.name
