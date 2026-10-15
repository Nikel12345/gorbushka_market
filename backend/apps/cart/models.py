from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    """
    Корзина пользователя. Отдельная модель (а не просто строки с user_id), чтобы
    было куда положить промокод, анонимную корзину по сессии и т.п.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name="пользователь",
    )

    class Meta:
        verbose_name = "корзина"
        verbose_name_plural = "корзины"

    def __str__(self):
        return f"Корзина {self.user}"


class CartItem(TimeStampedModel):
    """
    Позиция корзины. Цену не храним: в корзине всегда актуальная цена товара,
    фиксируется она только при оформлении заказа.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", verbose_name="корзина")
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="товар",
    )
    quantity = models.PositiveIntegerField("количество")

    class Meta:
        verbose_name = "позиция корзины"
        verbose_name_plural = "позиции корзины"
        ordering = ["id"]  # порядок добавления — строки не прыгают при изменении количества
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="cart_item_unique_product"),
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="cart_item_quantity_positive"),
        ]

    def __str__(self):
        return f"{self.product} × {self.quantity}"
