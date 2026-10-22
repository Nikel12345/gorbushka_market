"""
Статусы заказа: кто, из какого статуса и в какой может перевести заказ.

Путь зависит от того, кто исполняет доставку (DeliveryMethod.provider):

Самовывоз из магазина (provider=shop) — всё делает магазин:
    new → confirmed → ready («готов к выдаче») → completed («выдан»)

Доставка курьером (provider=market) — магазин собирает и передаёт, доставляет курьер:
    new → confirmed → ready («передан курьеру») → completed («доставлен»; ставит курьер)

Отмена: магазин — до выдачи (в т.ч. «покупатель не пришёл» для самовывоза),
покупатель — пока заказ новый, курьер — после передачи ему.

Новый способ доставки, роль курьера, код выдачи и т.п. меняют только TRANSITIONS
и change_status — API админки, покупателя и курьера остаются прежними.
"""
from django.db import transaction
from django.db.models import F

from apps.catalog.models import Product
from apps.core.exceptions import BusinessError
from apps.delivery.models import DeliveryMethod
from . import payments
from .models import Order, OrderStatusChange, Purchase

Status = Order.Status
Actor = OrderStatusChange.Actor
Provider = DeliveryMethod.Provider

SELLER, MARKET, BUYER = Actor.SELLER, Actor.MARKET, Actor.BUYER

# provider → {из статуса: {в статус: кто может}}
TRANSITIONS: dict[str, dict[str, dict[str, set[str]]]] = {
    Provider.SHOP: {
        Status.NEW: {Status.CONFIRMED: {SELLER}, Status.CANCELLED: {SELLER, BUYER}},
        Status.CONFIRMED: {Status.READY: {SELLER}, Status.CANCELLED: {SELLER}},
        Status.READY: {Status.COMPLETED: {SELLER}, Status.CANCELLED: {SELLER}},
    },
    Provider.MARKET: {
        Status.NEW: {Status.CONFIRMED: {SELLER}, Status.CANCELLED: {SELLER, BUYER}},
        Status.CONFIRMED: {Status.READY: {SELLER}, Status.CANCELLED: {SELLER}},
        Status.READY: {Status.COMPLETED: {MARKET}, Status.CANCELLED: {MARKET}},
    },
}

# Названия статусов, которые зависят от способа доставки
LABELS: dict[str, dict[str, str]] = {
    Provider.SHOP: {Status.READY: "Готов к выдаче", Status.COMPLETED: "Выдан"},
    Provider.MARKET: {Status.READY: "Передан курьеру", Status.COMPLETED: "Доставлен"},
}


def provider_of(order: Order) -> str:
    """Кто исполняет доставку заказа. Заказы до появления доставки ведёт продавец."""
    if order.shipment_id is None:
        return Provider.SHOP
    return order.shipment.delivery_method.provider


def label(order: Order, status: str) -> str:
    return LABELS[provider_of(order)].get(status) or Status(status).label


def status_label(order: Order) -> str:
    return label(order, order.status)


FINAL_STATUSES = {Status.COMPLETED, Status.CANCELLED}


def check_forced_change(order: Order, to: str) -> None:
    """
    Ручная смена (админка Django) разрешает любые переходы, кроме выхода из финального
    статуса: заказ уже выдан / деньги и остатки возвращены, обратного действия нет.
    """
    if order.status in FINAL_STATUSES and to != order.status:
        raise BusinessError(
            f"Заказ уже в финальном статусе «{status_label(order)}» — его нельзя изменить.",
            code="final_status",
        )


def available_statuses(order: Order, actor: str) -> list[str]:
    """Куда этот участник может перевести заказ сейчас — кнопки в интерфейсе."""
    targets = TRANSITIONS[provider_of(order)].get(order.status, {})
    return [status for status, actors in targets.items() if actor in actors]


@transaction.atomic
def change_status(order: Order, *, to: str, actor: str, user, force: bool = False) -> Order:
    """
    Переводит заказ в статус `to`. Отмена возвращает остатки и заплаченное заранее
    (orders.payments.refund_order). Всё в одной транзакции вместе с записью в журнал.

    force — ручная смена (админка Django): без таблицы переходов, но с теми же последствиями
    и без выхода из финального статуса (check_forced_change).
    """
    # Покупку блокируем первой: смены статусов заказов одной покупки идут по очереди,
    # иначе две параллельные отмены не поймут, кто последний (возврат доставки, статус оплаты).
    if order.purchase_id is not None:
        Purchase.objects.select_for_update().get(pk=order.purchase_id)
    # of=("self",): блокируем только строку заказа — PostgreSQL не умеет FOR UPDATE
    # по nullable-стороне LEFT JOIN (purchase и shipment бывают пустыми)
    order = (
        Order.objects.select_for_update(of=("self",))
        .select_related("purchase", "shipment__delivery_method")
        .get(pk=order.pk)
    )

    if force:
        check_forced_change(order, to)
        if to == order.status:
            return order
    elif to not in available_statuses(order, actor):
        raise BusinessError(
            f"Нельзя перевести заказ из «{status_label(order)}» в «{label(order, to)}».",
            code="invalid_transition",
        )

    from_status = order.status
    order.status = to
    order.save(update_fields=["status", "updated_at"])
    OrderStatusChange.objects.create(order=order, from_status=from_status, to_status=to, actor=actor, user=user)

    if to == Status.CANCELLED:
        _return_stock(order)
        payments.refund_order(order)
    if order.purchase_id is not None:
        _sync_payment_status(order.purchase)
    return order


def _return_stock(order: Order) -> None:
    for item in order.items.order_by("product_id"):
        Product.objects.filter(pk=item.product_id).update(quantity=F("quantity") + item.quantity)


def _sync_payment_status(purchase: Purchase) -> None:
    """
    С баланса: все заказы отменены → «возвращена».
    При получении: всё, что не отменено, выдано → «оплачена».
    """
    statuses = set(purchase.orders.values_list("status", flat=True))
    active = statuses - {Status.CANCELLED}

    new_status = purchase.payment_status
    if purchase.payment_method == Purchase.PaymentMethod.BALANCE:
        if not active and purchase.payment_status == Purchase.PaymentStatus.PAID:
            new_status = Purchase.PaymentStatus.REFUNDED
    elif active == {Status.COMPLETED}:
        new_status = Purchase.PaymentStatus.PAID

    if new_status != purchase.payment_status:
        purchase.payment_status = new_status
        purchase.save(update_fields=["payment_status", "updated_at"])
