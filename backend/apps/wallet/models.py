from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Wallet(TimeStampedModel):
    """
    Баланс пользователя. Поле balance — кеш суммы операций из WalletTransaction;
    менять его можно только через wallet.services.change_balance.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wallet",
        verbose_name="пользователь",
    )
    balance = models.DecimalField("баланс", max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = "кошелёк"
        verbose_name_plural = "кошельки"
        constraints = [
            models.CheckConstraint(condition=models.Q(balance__gte=0), name="wallet_balance_non_negative"),
        ]

    def __str__(self):
        return f"{self.user} — {self.balance}"


class WalletTransaction(models.Model):
    """Журнал операций по балансу. Записи только добавляются, не меняются и не удаляются."""

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Пополнение"
        WITHDRAWAL = "withdrawal", "Вывод"
        PAYMENT = "payment", "Оплата заказа"
        REFUND = "refund", "Возврат"
        ADJUSTMENT = "adjustment", "Корректировка"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="кошелёк",
    )
    # Положительная — зачисление, отрицательная — списание
    amount = models.DecimalField("сумма", max_digits=14, decimal_places=2)
    balance_after = models.DecimalField("баланс после", max_digits=14, decimal_places=2)
    kind = models.CharField("тип", max_length=20, choices=Kind.choices)
    description = models.CharField("описание", max_length=255, blank=True)
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        verbose_name = "операция по балансу"
        verbose_name_plural = "операции по балансу"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wallet", "-created_at", "-id"]),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(amount=0), name="wallet_transaction_amount_non_zero"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount}"
