"""
Деньги покупки в кошельке покупателя: бонусы, оплата с баланса, возвраты.
Выручка магазина в кошельки не попадает: приём денег будет на стороне платёжки.

Оформление (charge_purchase):
- бонусы (если покупатель включил): все доступные, но не больше BONUS_MAX_SHARE от итога.
  Распределяются по заказам и отправкам пропорционально суммам — так при отмене
  понятно, сколько бонусов вернуть;
- с баланса: остаток списывается с доступных денег;
- при получении: остаток покупатель платит при вручении (Order/Shipment.amount_due).

Отмена (refund_order): покупателю — то, что он заплатил заранее, в те же части баланса
(бонусы в бонусы, деньги в доступные); доставку — когда отменена вся отправка.
"""
from decimal import ROUND_DOWN, Decimal

from django.conf import settings

from apps.wallet.models import Bucket, WalletOperation
from apps.wallet.services import Entry, get_wallet, post_operation

from .models import Order, Purchase, Shipment

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
Kind = WalletOperation.Kind


def bonus_to_use(user, total: Decimal) -> Decimal:
    """Сколько бонусов спишется: все, но не больше BONUS_MAX_SHARE от суммы покупки."""
    cap = (total * settings.BONUS_MAX_SHARE).quantize(CENT, rounding=ROUND_DOWN)
    return min(get_wallet(user).bonus, cap)


def allocate(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Делит сумму пропорционально весам до копейки; остаток копеек — самой большой доле."""
    total = sum(weights, ZERO)
    if not amount or not total:
        return [ZERO for _ in weights]
    shares = [(amount * weight / total).quantize(CENT, rounding=ROUND_DOWN) for weight in weights]
    biggest = max(range(len(weights)), key=lambda i: weights[i])
    shares[biggest] += amount - sum(shares, ZERO)
    return shares


def charge_purchase(purchase: Purchase, *, use_bonus: bool) -> None:
    """Списывает оплату за только что оформленную покупку (внутри транзакции оформления)."""
    buyer = purchase.buyer
    orders = list(purchase.orders.all())
    shipments = [shipment for shipment in purchase.shipments.all() if shipment.price > 0]

    bonus = bonus_to_use(buyer, purchase.total_amount) if use_bonus else ZERO
    weights = [order.total_amount for order in orders] + [shipment.price for shipment in shipments]
    for payable, share in zip([*orders, *shipments], allocate(bonus, weights)):
        payable.bonus_amount = share
    Order.objects.bulk_update(orders, ["bonus_amount"])
    Shipment.objects.bulk_update(shipments, ["bonus_amount"])

    purchase.bonus_amount = bonus
    paid_by_balance = purchase.payment_method == Purchase.PaymentMethod.BALANCE
    post_operation(
        kind=Kind.PAYMENT,
        entries=[
            Entry(buyer, Bucket.BONUS, -bonus),
            Entry(buyer, Bucket.AVAILABLE, -(purchase.total_amount - bonus) if paid_by_balance else ZERO),
        ],
        description=f"Оплата покупки #{purchase.pk}",
    )
    if paid_by_balance:
        purchase.payment_status = Purchase.PaymentStatus.PAID
    purchase.save(update_fields=["bonus_amount", "payment_status", "updated_at"])


def refund_order(order: Order) -> None:
    """Заказ отменён: покупателю — заплаченное заранее."""
    purchase = order.purchase
    if purchase is None:
        return
    paid_by_balance = purchase.payment_method == Purchase.PaymentMethod.BALANCE

    bonus_back = order.bonus_amount
    money_back = order.total_amount - order.bonus_amount if paid_by_balance else ZERO
    shipment = order.shipment
    if shipment is not None and not shipment.orders.exclude(status=Order.Status.CANCELLED).exists():
        bonus_back += shipment.bonus_amount
        if paid_by_balance:
            money_back += shipment.price - shipment.bonus_amount

    post_operation(
        kind=Kind.REFUND,
        entries=[Entry(purchase.buyer, Bucket.BONUS, bonus_back), Entry(purchase.buyer, Bucket.AVAILABLE, money_back)],
        description=f"Возврат за заказ #{order.pk} (покупка #{purchase.pk})",
    )
