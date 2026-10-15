from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import BusinessError

from .models import Wallet, WalletTransaction


def get_balance(user) -> Decimal:
    """Баланс без создания кошелька: у пользователя без операций он просто 0."""
    wallet = Wallet.objects.filter(user=user).only("balance").first()
    return wallet.balance if wallet else Decimal("0.00")


@transaction.atomic
def change_balance(*, user, amount: Decimal, kind: str, description: str = "") -> WalletTransaction:
    """
    Единственный способ изменить баланс. Блокирует кошелёк до конца транзакции,
    поэтому параллельные операции не перезапишут друг друга, и пишет операцию
    в журнал. amount > 0 — зачисление, amount < 0 — списание.
    """
    amount = Decimal(amount)
    if amount == 0:
        raise BusinessError("Сумма операции не может быть нулевой.", code="zero_amount")

    Wallet.objects.get_or_create(user=user)
    wallet = Wallet.objects.select_for_update().get(user=user)

    new_balance = wallet.balance + amount
    if new_balance < 0:
        raise BusinessError("Недостаточно средств на балансе.", code="insufficient_funds")

    wallet.balance = new_balance
    wallet.save(update_fields=["balance", "updated_at"])

    return WalletTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        balance_after=new_balance,
        kind=kind,
        description=description,
    )
