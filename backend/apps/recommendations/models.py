from django.db import models

from apps.catalog.models import Product


class BoughtTogether(models.Model):
    """
    «С этим товаром часто покупают»: место товара related в топе товара product.
    Хранится только топ (services.TOP_SIZE строк на товар), а не все пары товаров.
    Напрямую не меняется — его пересчитывает recommendations.services.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="bought_together",
        verbose_name="товар",
    )
    # Обратная связь: Product.objects.filter(bought_with__product=X) — товары из топа X
    related = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="bought_with",
        verbose_name="покупают вместе с ним",
    )
    purchases_count = models.PositiveIntegerField("совместных покупок")
    position = models.PositiveSmallIntegerField("место")

    class Meta:
        verbose_name = "часто покупают вместе"
        verbose_name_plural = "часто покупают вместе"
        ordering = ["product", "position"]
        constraints = [
            models.UniqueConstraint(fields=["product", "position"], name="recommendations_bought_together_position"),
            models.UniqueConstraint(fields=["product", "related"], name="recommendations_bought_together_pair"),
        ]

    def __str__(self):
        return f"{self.product} → {self.related}"
