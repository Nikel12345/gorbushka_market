from django.db import models

from apps.core.models import TimeStampedModel


class ShopQuerySet(models.QuerySet):
    def current(self):
        """
        Магазин. Он один: заводится в админке Django, через API не создаётся.
        None — ещё не заведён.
        """
        return self.order_by("id").first()

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
    name = models.CharField("название", max_length=255)
    description = models.TextField("описание", blank=True)
    # Где покупатель забирает товар при самовывозе: павильон, ряд, место
    address = models.CharField("адрес", max_length=255, blank=True)

    objects = ShopQuerySet.as_manager()

    class Meta:
        verbose_name = "магазин"
        verbose_name_plural = "магазины"
        ordering = ["id"]

    def __str__(self):
        return self.name
