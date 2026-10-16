"""
Кошелёк. Единственная точка изменения балансов — post_operation: она блокирует
кошельки, проверяет, что ни одна часть не уходит в минус, обновляет кеш балансов
и пишет проводки — всё в одной транзакции.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.db import transaction

from apps.core.exceptions import BusinessError

from .models import Bucket, Wallet, WalletOperation, WalletTransaction

MESSAGES = {
    Bucket.AVAILABLE: "Недостаточно средств на балансе.",
    Bucket.BONUS: "Недостаточно бонусов.",
    Bucket.FROZEN: "Недостаточно замороженных средств.",
}


@dataclass(frozen=True)
class Entry:
    user: object
    bucket: str
    amount: Decimal


@dataclass(frozen=True)
class WalletSummary:
    available: Decimal
    bonus: Decimal
    frozen: Decimal

    @property
    def spendable(self) -> Decimal:
        """Для покупок: реальные деньги (без долга) + бонусы."""
        return max(self.available, Decimal("0.00")) + self.bonus

    @property
    def balance(self) -> Decimal:
        """Совместимость со старым API: «баланс» = реальные деньги."""
        return self.available


ZERO = Decimal("0.00")


def get_wallet(user) -> WalletSummary:
    """Балансы без создания кошелька: у пользователя без операций всё по нулям."""
    wallet = Wallet.objects.filter(user=user).only("available", "bonus", "frozen").first()
    if wallet is None:
        return WalletSummary(ZERO, ZERO, ZERO)
    return WalletSummary(wallet.available, wallet.bonus, wallet.frozen)


def get_balance(user) -> Decimal:
    """Реальные деньги (available). Оставлено для совместимости."""
    return get_wallet(user).available


@transaction.atomic
def post_operation(
    *,
    kind: str,
    entries: Iterable[Entry],
    description: str = "",
    allow_debt: bool = False,
) -> WalletOperation | None:
    """
    Проводит операцию из нескольких проводок. Нулевые проводки пропускаются;
    если не осталось ни одной — операция не создаётся (None).

    allow_debt — разрешить available уйти в минус (долг продавца по комиссии).
    """
    entries = [Entry(e.user, e.bucket, Decimal(e.amount)) for e in entries if Decimal(e.amount) != 0]
    if not entries:
        return None

    # Кошельки блокируем в порядке id пользователей — параллельные операции
    # с теми же кошельками не уйдут в дедлок.
    user_ids = sorted({entry.user.pk for entry in entries})
    for user_id in user_ids:
        Wallet.objects.get_or_create(user_id=user_id)
    wallets = {w.user_id: w for w in Wallet.objects.select_for_update().filter(user_id__in=user_ids).order_by("user_id")}

    operation = WalletOperation.objects.create(kind=kind, description=description)
    rows = []
    for entry in entries:
        wallet = wallets[entry.user.pk]
        new_value = getattr(wallet, entry.bucket) + entry.amount
        if new_value < 0 and not (allow_debt and entry.bucket == Bucket.AVAILABLE):
            code = "insufficient_bonus" if entry.bucket == Bucket.BONUS else "insufficient_funds"
            raise BusinessError(MESSAGES[entry.bucket], code=code)
        setattr(wallet, entry.bucket, new_value)
        rows.append(
            WalletTransaction(
                wallet=wallet,
                operation=operation,
                bucket=entry.bucket,
                amount=entry.amount,
                balance_after=new_value,
                kind=kind,
                description=description,
            )
        )

    for wallet in wallets.values():
        wallet.save(update_fields=["available", "bonus", "frozen", "updated_at"])
    WalletTransaction.objects.bulk_create(rows)
    return operation


def change_balance(
    *,
    user,
    amount: Decimal,
    kind: str,
    description: str = "",
    bucket: str = Bucket.AVAILABLE,
) -> WalletTransaction:
    """Простая операция из одной проводки (пополнение, начисление бонусов, корректировка)."""
    if Decimal(amount) == 0:
        raise BusinessError("Сумма операции не может быть нулевой.", code="zero_amount")
    operation = post_operation(kind=kind, entries=[Entry(user, bucket, amount)], description=description)
    return operation.entries.get()


def adjust_wallet(*, user, deltas: dict[str, Decimal], description: str = "") -> WalletOperation | None:
    """
    Ручная корректировка (админка): изменить части баланса на заданные разницы.
    Проводится обычной операцией — журнал и кеш балансов остаются согласованными.
    available может уйти в минус (долг), bonus и frozen — нет.
    """
    return post_operation(
        kind=WalletOperation.Kind.ADJUSTMENT,
        entries=[Entry(user, bucket, delta) for bucket, delta in deltas.items()],
        description=description,
        allow_debt=True,
    )
