from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel
from apps.shops.models import Shop


class OrderQuerySet(models.QuerySet):
    def with_details(self):
        """Всё, что нужно для вывода заказа в списке, без N+1."""
        return self.select_related("shop", "buyer").prefetch_related("items")


class Order(TimeStampedModel):
    """Заказ всегда в одном магазине: корзина с товарами разных магазинов делится на заказы."""

    class Status(models.TextChoices):
        NEW = "new", "Новый"
        CONFIRMED = "confirmed", "Подтверждён"
        COMPLETED = "completed", "Выполнен"
        CANCELLED = "cancelled", "Отменён"

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="магазин",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="покупатель",
    )
    status = models.CharField(
        "статус",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    # Фиксируется при оформлении и дальше не пересчитывается
    total_amount = models.DecimalField("сумма", max_digits=12, decimal_places=2)

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = "заказ"
        verbose_name_plural = "заказы"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["shop", "-created_at"]),
            models.Index(fields=["buyer", "-created_at", "-id"], name="orders_buyer_history_idx"),
        ]

    def __str__(self):
        return f"Заказ #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="заказ",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="товар",
    )
    # Снимок товара на момент заказа: последующие правки товара не меняют историю
    title = models.CharField("название", max_length=255)
    price = models.DecimalField("цена", max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField("количество")

    class Meta:
        verbose_name = "позиция заказа"
        verbose_name_plural = "позиции заказа"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="orders_item_quantity_positive"),
        ]

    def __str__(self):
        return f"{self.title} × {self.quantity}"

    @property
    def total(self):
        return self.price * self.quantity
