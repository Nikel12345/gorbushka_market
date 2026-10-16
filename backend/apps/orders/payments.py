"""
Деньги покупки: бонусы, оплата с баланса, выручка продавцов, комиссия маркета.
Кошелёк только у пользователя: выручка магазина приходит в кошелёк его владельца.

Оформление (charge_purchase):
- бонусы (если покупатель включил): все доступные, но не больше BONUS_MAX_SHARE от итога.
  Распределяются по заказам и отправкам пропорционально суммам — так при отмене
  понятно, сколько бонусов вернуть;
- с баланса: остаток списывается с доступных денег, выручка продавцов замораживается;
- при получении: остаток покупатель платит при вручении (Order/Shipment.amount_due);
- комиссия маркета фиксируется в заказе по текущей ставке.

Выдача (settle_order) — выручка продавца за вычетом комиссии:
- с баланса: размораживается (frozen → available);
- при получении, самовывоз: продавец сам взял amount_due, маркет доплачивает бонусную
  часть минус комиссия (может уйти в минус — долг продавца перед маркетом);
- при получении, курьер маркета: деньги взял курьер, продавцу — вся выручка.

Отмена (refund_order):
- покупателю — то, что он заплатил заранее, в те же части баланса (бонусы в бонусы,
  деньги в доступные); доставку — когда отменена вся отправка;
- замороженная выручка продавца снимается.
"""
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from django.conf import settings

from apps.delivery.models import DeliveryMethod
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


def commission_for(amount: Decimal) -> Decimal:
    return (amount * settings.MARKET_COMMISSION_RATE).quantize(CENT, rounding=ROUND_HALF_UP)


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
    orders = list(purchase.orders.select_related("shop__owner"))
    shipments = [shipment for shipment in purchase.shipments.all() if shipment.price > 0]

    for order in orders:
        order.commission_amount = commission_for(order.total_amount)

    bonus = bonus_to_use(buyer, purchase.total_amount) if use_bonus else ZERO
    weights = [order.total_amount for order in orders] + [shipment.price for shipment in shipments]
    for payable, share in zip([*orders, *shipments], allocate(bonus, weights)):
        payable.bonus_amount = share
    Order.objects.bulk_update(orders, ["bonus_amount", "commission_amount"])
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
        # Деньги уже у маркета: выручка продавцов ждёт выдачи заказов
        post_operation(
            kind=Kind.SALE,
            entries=[Entry(order.shop.owner, Bucket.FROZEN, order.total_amount) for order in orders],
            description=f"Выручка по покупке #{purchase.pk} (до выдачи заказов)",
        )
        purchase.payment_status = Purchase.PaymentStatus.PAID
    purchase.save(update_fields=["bonus_amount", "payment_status", "updated_at"])


def settle_order(order: Order, *, provider: str) -> None:
    """Заказ выдан: выручка продавцу за вычетом комиссии."""
    purchase = order.purchase
    if purchase is None:
        return
    owner = order.shop.owner
    if purchase.payment_method == Purchase.PaymentMethod.BALANCE:
        entries = [
            Entry(owner, Bucket.FROZEN, -order.total_amount),
            Entry(owner, Bucket.AVAILABLE, order.seller_amount),
        ]
    elif provider == DeliveryMethod.Provider.SHOP:
        # Наличные (amount_due) продавец взял сам — доплачиваем бонусную часть, удерживаем комиссию
        entries = [Entry(owner, Bucket.AVAILABLE, order.bonus_amount - order.commission_amount)]
    else:
        # Наличные взял курьер маркета — продавцу вся выручка
        entries = [Entry(owner, Bucket.AVAILABLE, order.seller_amount)]
    post_operation(
        kind=Kind.SALE_RELEASE,
        entries=entries,
        description=f"Выручка за заказ #{order.pk} (комиссия {order.commission_amount})",
        allow_debt=True,
    )


def refund_order(order: Order) -> None:
    """Заказ отменён: покупателю — заплаченное заранее, продавцу — снять замороженную выручку."""
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
    if paid_by_balance:
        post_operation(
            kind=Kind.SALE_CANCEL,
            entries=[Entry(order.shop.owner, Bucket.FROZEN, -order.total_amount)],
            description=f"Отмена заказа #{order.pk}",
        )
