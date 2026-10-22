from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Bucket(models.TextChoices):
    """Части баланса. «Для покупок» не хранится: это available + bonus."""

    AVAILABLE = "available", "Доступно для вывода"
    BONUS = "bonus", "Бонусы"


class Wallet(TimeStampedModel):
    """
    Кошелёк покупателя: баланс и бонусы. Выручка магазина сюда не попадает (приём денег —
    на стороне платёжки). Поля — кеш суммы проводок из WalletTransaction по каждой части;
    менять их можно только через wallet.services (post_operation / change_balance).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wallet",
        verbose_name="пользователь",
    )
    # Реальные деньги: можно тратить и выводить. В минус уходит только ручной корректировкой в админке.
    available = models.DecimalField("доступно для вывода", max_digits=14, decimal_places=2, default=0)
    # Только на покупки, не выводятся
    bonus = models.DecimalField("бонусы", max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "кошелёк"
        verbose_name_plural = "кошельки"
        constraints = [
            models.CheckConstraint(condition=models.Q(bonus__gte=0), name="wallet_bonus_non_negative"),
        ]

    def __str__(self):
        return f"{self.user} — {self.available}"

    @property
    def spendable(self):
        """Для покупок: реальные деньги (без минуса) + бонусы."""
        return max(self.available, 0) + self.bonus


class WalletOperation(models.Model):
    """
    Одно бизнес-событие (оплата покупки, возврат, начисление бонусов...). Состоит из
    проводок по кошелькам и их частям; все проводки операции — в одной транзакции.
    """

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Пополнение"
        WITHDRAWAL = "withdrawal", "Вывод"
        PAYMENT = "payment", "Оплата покупки"
        REFUND = "refund", "Возврат"
        ADJUSTMENT = "adjustment", "Корректировка"
        BONUS = "bonus", "Начисление бонусов"

    kind = models.CharField("тип", max_length=20, choices=Kind.choices)
    description = models.CharField("описание", max_length=255, blank=True)
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        verbose_name = "операция по кошельку"
        verbose_name_plural = "операции по кошелькам"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk}"


class WalletTransaction(models.Model):
    """Проводка: изменение одной части одного кошелька. Записи только добавляются."""

    # Совместимость: раньше тип жил на проводке, теперь — на операции
    Kind = WalletOperation.Kind

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="кошелёк",
    )
    operation = models.ForeignKey(
        WalletOperation,
        on_delete=models.PROTECT,
        null=True,  # проводки до появления операций
        related_name="entries",
        verbose_name="операция",
    )
    bucket = models.CharField("часть баланса", max_length=20, choices=Bucket.choices, default=Bucket.AVAILABLE)
    # Положительная — зачисление, отрицательная — списание
    amount = models.DecimalField("сумма", max_digits=14, decimal_places=2)
    # Значение этой части баланса после проводки
    balance_after = models.DecimalField("баланс после", max_digits=14, decimal_places=2)
    kind = models.CharField("тип", max_length=20, choices=WalletOperation.Kind.choices)
    description = models.CharField("описание", max_length=255, blank=True)
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        verbose_name = "проводка по кошельку"
        verbose_name_plural = "проводки по кошелькам"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wallet", "-created_at", "-id"]),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(amount=0), name="wallet_transaction_amount_non_zero"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount} ({self.bucket})"
