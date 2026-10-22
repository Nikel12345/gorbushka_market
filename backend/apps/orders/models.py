from django.conf import settings
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel
from apps.delivery.models import DeliveryMethod
from apps.shops.models import Shop

# Структура покупки:
#   Purchase (покупка: покупатель, оплата, итог)
#    ├── Order (заказ = магазин × отправка: статус, сумма товаров) ← его видит продавец
#    │    ├── OrderItem (позиция: товар, снимок цены)
#    │    └── OrderStatusChange (журнал смены статусов)
#    └── Shipment (отправка: способ доставки, слот, адрес, цена доставки; в ней заказы одного
#                  или нескольких магазинов)


def _items_with_product():
    """Позиции заказа вместе с товаром (фото в API) — тем же запросом."""
    return models.Prefetch("items", queryset=OrderItem.objects.select_related("product"))


class PurchaseQuerySet(models.QuerySet):
    def with_details(self):
        """Покупка целиком — заказы магазинов с позициями и отправки — без N+1."""
        orders = Order.objects.select_related("shop", "shipment__delivery_method").prefetch_related(
            _items_with_product()
        )
        return self.prefetch_related(
            models.Prefetch("orders", queryset=orders.order_by("id")),
            "shipments__delivery_method",
            "shipments__shop",
        )


class Purchase(TimeStampedModel):
    """
    Покупка — то, что покупатель оформил одной кнопкой и оплачивает одним платежом.
    Делится на заказы магазинов (Order) и отправки (Shipment).
    """

    class PaymentMethod(models.TextChoices):
        BALANCE = "balance", "С баланса"
        ON_DELIVERY = "on_delivery", "При получении"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Не оплачена"
        PAID = "paid", "Оплачена"
        # Оплачена с баланса, все заказы отменены, деньги вернулись на баланс
        REFUNDED = "refunded", "Возвращена"

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchases",
        verbose_name="покупатель",
    )
    payment_method = models.CharField("способ оплаты", max_length=20, choices=PaymentMethod.choices)
    payment_status = models.CharField(
        "статус оплаты",
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )
    # Суммы фиксируются при оформлении и дальше не пересчитываются
    items_total = models.DecimalField("товары", max_digits=12, decimal_places=2)
    delivery_total = models.DecimalField("доставка", max_digits=12, decimal_places=2)
    total_amount = models.DecimalField("итого", max_digits=12, decimal_places=2)
    # Сколько из итога оплачено бонусами (списаны при оформлении, при любом способе оплаты).
    # Распределено по заказам и отправкам — их bonus_amount.
    bonus_amount = models.DecimalField("оплачено бонусами", max_digits=12, decimal_places=2, default=0)
    comment = models.TextField("комментарий", blank=True)

    objects = PurchaseQuerySet.as_manager()

    class Meta:
        verbose_name = "покупка"
        verbose_name_plural = "покупки"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["buyer", "-created_at", "-id"], name="orders_purchase_history_idx"),
        ]

    def __str__(self):
        return f"Покупка #{self.pk}"


class Shipment(models.Model):
    """
    Отправка: заказы покупки, которые едут одной доставкой. Стоимость доставки
    берётся один раз за отправку, а не за каждую позицию. Как позиции собираются
    в отправки — решает orders.checkout.shipment_key.
    """

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="shipments",
        verbose_name="покупка",
    )
    # Название способа не снимаем: справочник ведёт маркет, способы не удаляются (PROTECT).
    # Цена — снимок: тариф может измениться.
    delivery_method = models.ForeignKey(
        DeliveryMethod,
        on_delete=models.PROTECT,
        related_name="shipments",
        verbose_name="способ доставки",
    )
    # Для доставки силами продавца (самовывоз из павильона) — его магазин.
    # Для логистики маркета пусто: одна отправка собирает товары разных магазинов.
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="shipments",
        verbose_name="магазин",
    )
    price = models.DecimalField("стоимость доставки", max_digits=10, decimal_places=2)
    # Доля бонусов покупки, пришедшаяся на доставку
    bonus_amount = models.DecimalField("оплачено бонусами", max_digits=10, decimal_places=2, default=0)
    # Куда доставить (курьер) или откуда забрать (самовывоз — снимок адреса магазина)
    address = models.CharField("адрес", max_length=500, blank=True)
    slot_date = models.DateField("дата доставки", null=True, blank=True)
    slot_start = models.TimeField("с", null=True, blank=True)
    slot_end = models.TimeField("до", null=True, blank=True)

    class Meta:
        verbose_name = "отправка"
        verbose_name_plural = "отправки"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="orders_shipment_price_non_negative"),
        ]

    def __str__(self):
        return f"{self.delivery_method} (покупка #{self.purchase_id})"

    @property
    def amount_due(self):
        """Сколько получить за доставку при вручении (только для оплаты при получении)."""
        if self.purchase.payment_method != Purchase.PaymentMethod.ON_DELIVERY:
            return 0
        return self.price - self.bonus_amount


class OrderQuerySet(models.QuerySet):
    def with_details(self):
        """Всё, что нужно для вывода заказа в списке, без N+1."""
        return self.select_related(
            "shop", "buyer", "purchase", "shipment__delivery_method", "shipment__purchase"
        ).prefetch_related(
            _items_with_product()
        )


class Order(TimeStampedModel):
    """
    Заказ — часть покупки от одного магазина с одним способом доставки (магазин × отправка).
    Продавец видит и ведёт (подтверждает, собирает, выдаёт) только свои заказы.
    Кто и куда может перевести статус — orders.statuses.
    """

    class Status(models.TextChoices):
        NEW = "new", "Новый"
        CONFIRMED = "confirmed", "Подтверждён"
        # Самовывоз — «готов к выдаче», курьер маркета — «передан курьеру» (см. statuses.status_label)
        READY = "ready", "Готов"
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
    # Покупка, частью которой является заказ. Пусто — у заказов, созданных до появления покупок.
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="покупка",
    )
    # Как доставляется заказ. Пусто — у заказов, созданных до появления доставки.
    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name="отправка",
    )
    # Сумма товаров магазина (без доставки). Фиксируется при оформлении и дальше не пересчитывается
    total_amount = models.DecimalField("сумма", max_digits=12, decimal_places=2)
    # Доля бонусов покупки, пришедшаяся на этот заказ (столько бонусов вернётся при отмене)
    bonus_amount = models.DecimalField("оплачено бонусами", max_digits=12, decimal_places=2, default=0)

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

    @property
    def payment_method(self) -> str | None:
        return self.purchase.payment_method if self.purchase_id else None

    @property
    def amount_due(self):
        """Сколько получить с покупателя при выдаче: товары минус бонусы (только при оплате при получении)."""
        if self.payment_method != Purchase.PaymentMethod.ON_DELIVERY:
            return 0
        return self.total_amount - self.bonus_amount


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


class OrderStatusChange(models.Model):
    """Журнал смены статусов заказа: кто, когда, из какого в какой. Записи только добавляются."""

    class Actor(models.TextChoices):
        SELLER = "seller", "Магазин"
        MARKET = "market", "Курьер"
        BUYER = "buyer", "Покупатель"
        # Ручная смена в админке Django: любые переходы из незавершённых статусов
        ADMIN = "admin", "Администратор"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_changes", verbose_name="заказ")
    from_status = models.CharField("было", max_length=20, choices=Order.Status.choices)
    to_status = models.CharField("стало", max_length=20, choices=Order.Status.choices)
    actor = models.CharField("кто", max_length=20, choices=Actor.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="пользователь",
    )
    created_at = models.DateTimeField("когда", auto_now_add=True)

    class Meta:
        verbose_name = "смена статуса заказа"
        verbose_name_plural = "смены статусов заказов"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.from_status} → {self.to_status}"
