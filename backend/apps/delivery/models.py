from django.db import models

from apps.core.models import TimeStampedModel


class DeliveryMethodQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def available_for_shop(self, shop):
        """
        Способы, которые магазин может назначать своим товарам.
        Единственная точка этого правила: сейчас — все активные; позже —
        подключение магазина к логистике маркета, свои способы магазина и т.п.
        """
        return self.active()


class DeliveryMethod(TimeStampedModel):
    """Справочник способов доставки. Ведёт маркет (админка)."""

    class Kind(models.TextChoices):
        PICKUP = "pickup", "Самовывоз"
        COURIER = "courier", "Курьер"

    class Provider(models.TextChoices):
        # Кто исполняет доставку. От этого зависит, как товары группируются при оформлении:
        # доставка продавца — в пределах магазина, логистика маркета может объединять магазины.
        SHOP = "shop", "Продавец"
        MARKET = "market", "Маркет"

    code = models.SlugField("код", max_length=50, unique=True)
    name = models.CharField("название", max_length=255)
    description = models.TextField("описание", blank=True)
    kind = models.CharField("тип", max_length=20, choices=Kind.choices)
    provider = models.CharField("исполнитель", max_length=20, choices=Provider.choices)
    price = models.DecimalField("стоимость", max_digits=10, decimal_places=2, default=0)
    requires_address = models.BooleanField("нужен адрес", default=False)
    # Срок доставки в днях. Пусто — срока нет (самовывоз).
    eta_min_days = models.PositiveSmallIntegerField("срок от, дней", null=True, blank=True)
    eta_max_days = models.PositiveSmallIntegerField("срок до, дней", null=True, blank=True)
    # На сколько дней вперёд можно выбрать дату и интервал. 0 — выбор времени не нужен.
    slot_days_ahead = models.PositiveSmallIntegerField("дней для выбора времени", default=0)
    is_active = models.BooleanField("активен", default=True)
    sort_order = models.PositiveSmallIntegerField("порядок", default=0)

    objects = DeliveryMethodQuerySet.as_manager()

    class Meta:
        verbose_name = "способ доставки"
        verbose_name_plural = "способы доставки"
        ordering = ["sort_order", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="delivery_method_price_non_negative"),
            models.CheckConstraint(
                condition=(
                    models.Q(eta_min_days__isnull=True, eta_max_days__isnull=True)
                    | models.Q(
                        eta_min_days__isnull=False,
                        eta_max_days__isnull=False,
                        eta_min_days__lte=models.F("eta_max_days"),
                    )
                ),
                name="delivery_method_eta_range",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def has_slots(self) -> bool:
        return self.slot_days_ahead > 0


class DeliveryTimeWindow(models.Model):
    """Интервал доставки для способа с выбором времени (например, 10:00–14:00)."""

    method = models.ForeignKey(
        DeliveryMethod,
        on_delete=models.CASCADE,
        related_name="time_windows",
        verbose_name="способ доставки",
    )
    start_time = models.TimeField("с")
    end_time = models.TimeField("до")
    is_active = models.BooleanField("активен", default=True)

    class Meta:
        verbose_name = "интервал доставки"
        verbose_name_plural = "интервалы доставки"
        ordering = ["start_time", "id"]
        constraints = [
            models.UniqueConstraint(fields=["method", "start_time", "end_time"], name="delivery_window_unique"),
            models.CheckConstraint(condition=models.Q(end_time__gt=models.F("start_time")), name="delivery_window_order"),
        ]

    def __str__(self):
        return f"{self.start_time:%H:%M}–{self.end_time:%H:%M}"
