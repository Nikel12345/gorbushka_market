"""
Оформление покупки из корзины.

1. get_checkout   (GET  /me/checkout/)       — что можно купить и какие способы доставки у каждой позиции.
2. quote          (POST /me/checkout/quote/) — покупатель выбрал способы: отправки и итоговая сумма.
3. place_purchase (POST /me/checkout/)       — оформить покупку одной транзакцией.

Оформить может и гость (корзина по сессии): на последнем шаге он указывает почту и пароль,
place_guest_purchase оформляет покупку в его аккаунт или в новый — в одной транзакции.

Способ доставки покупатель выбирает у каждой позиции. Позиции с одинаковой
доставкой объединяются в отправку (Shipment), и доставка оплачивается один раз
за отправку, а не за каждую позицию (см. shipment_key):
- логистика маркета (provider=market) — одна отправка на способ, даже если
  товары из разных магазинов;
- доставка силами продавца (provider=shop, например самовывоз из павильона) —
  отправка на способ в каждом магазине.
Время доставки выбирается одно на способ, адрес — один на покупку: одна поездка курьера.

Позиции, которые купить нельзя (снят с продажи, не хватает остатка,
нет способа доставки), не оформляются и остаются в корзине.
"""
import datetime
from collections import defaultdict
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import prefetch_related_objects

from apps.cart.models import Cart, CartItem
from apps.cart.services import CartLine, get_cart
from apps.catalog.models import Product
from apps.core.exceptions import BusinessConflict, BusinessError
from apps.delivery.models import DeliveryMethod
from apps.delivery.services import DeliverySlot, validate_slot
from apps.recommendations import services as bought_together
from apps.shops.models import Shop
from apps.users.models import User
from apps.users.services import register_user, update_profile
from apps.wallet.services import WalletSummary, get_wallet

from . import payments
from .models import Purchase, Shipment
from .services import OrderLine, create_order

# --- Что покупатель видит на странице оформления ---


@dataclass(frozen=True)
class CheckoutProblem:
    code: str
    detail: str


@dataclass(frozen=True)
class CheckoutLine(CartLine):
    """Позиция корзины при оформлении: доступные способы доставки или причина, почему купить нельзя."""

    delivery_methods: tuple[DeliveryMethod, ...] = ()
    problem: CheckoutProblem | None = None

    @property
    def can_buy(self) -> bool:
        return self.problem is None

    @property
    def pickup_address(self) -> str | None:
        """Где забрать товар при самовывозе из павильона."""
        return self.product.shop.address or None


@dataclass(frozen=True)
class CheckoutPreview:
    lines: list[CheckoutLine]
    balance: Decimal  # доступные деньги — для оплаты с баланса
    bonus: Decimal  # бонусы — переключатель «оплатить бонусами»
    bonus_max_share: Decimal  # какую часть итога можно оплатить бонусами
    guest: bool = False  # оформляет гость: баланса нет

    @property
    def items(self) -> list[CheckoutLine]:
        return [line for line in self.lines if line.can_buy]

    @property
    def unavailable_items(self) -> list[CheckoutLine]:
        return [line for line in self.lines if not line.can_buy]

    @property
    def items_total(self) -> Decimal:
        return sum((line.total for line in self.items), Decimal("0.00"))

    @property
    def can_checkout(self) -> bool:
        return bool(self.items)

    @property
    def payment_methods(self) -> list[dict]:
        return [
            {"code": code, "name": name}
            for code, name in Purchase.PaymentMethod.choices
            if not (self.guest and code == Purchase.PaymentMethod.BALANCE)
        ]


def _problem(line: CartLine, methods: tuple) -> CheckoutProblem | None:
    if line.available_quantity == 0:
        return CheckoutProblem("product_unavailable", "Товар снят с продажи или закончился.")
    if not line.is_available:
        return CheckoutProblem("insufficient_stock", f"В наличии только {line.available_quantity} шт.")
    if not methods:
        return CheckoutProblem("no_delivery", "Для товара нет доступных способов доставки.")
    return None


def _checkout_lines(cart: Cart | None) -> list[CheckoutLine]:
    content = get_cart(cart)
    prefetch_related_objects([line.product for line in content.lines], "delivery_methods")

    allowed_by_shop: dict[int, set[int]] = {}
    lines = []
    for line in content.lines:
        shop = line.product.shop
        if shop.id not in allowed_by_shop:
            allowed_by_shop[shop.id] = set(
                DeliveryMethod.objects.available_for_shop(shop).values_list("id", flat=True)
            )
        methods = tuple(
            method
            for method in line.product.delivery_methods.all()
            if method.id in allowed_by_shop[shop.id]
            # самовывоз из магазина без адреса не предлагаем (старые товары)
            and not (method.needs_shop_address and not shop.address)
        )
        lines.append(
            CheckoutLine(item=line.item, delivery_methods=methods, problem=_problem(line, methods))
        )
    return lines


def get_checkout(cart: Cart | None, user: User | None) -> CheckoutPreview:
    """user=None — гость: баланса и бонусов у него нет."""
    wallet = get_wallet(user) if user is not None else WalletSummary(Decimal("0.00"), Decimal("0.00"))
    return CheckoutPreview(
        lines=_checkout_lines(cart),
        balance=wallet.available,
        bonus=wallet.bonus,
        bonus_max_share=settings.BONUS_MAX_SHARE,
        guest=user is None,
    )


# --- Выбор покупателя и расчёт ---


@dataclass(frozen=True)
class DeliveryChoice:
    product_id: int
    delivery_method_id: int


@dataclass(frozen=True)
class SlotChoice:
    delivery_method_id: int
    date: datetime.date
    window_id: int


@dataclass
class PlannedShipment:
    method: DeliveryMethod
    shop: Shop | None
    lines: list[CheckoutLine] = field(default_factory=list)

    @property
    def price(self) -> Decimal:
        return self.method.price

    @property
    def product_ids(self) -> list[int]:
        return [line.product.id for line in self.lines]


@dataclass(frozen=True)
class CheckoutPlan:
    lines: list[CheckoutLine]
    shipments: list[PlannedShipment]
    # Сколько спишется бонусами (если покупатель включил переключатель)
    bonus_amount: Decimal = Decimal("0.00")

    @property
    def items_total(self) -> Decimal:
        return sum((line.total for line in self.lines), Decimal("0.00"))

    @property
    def delivery_total(self) -> Decimal:
        return sum((shipment.price for shipment in self.shipments), Decimal("0.00"))

    @property
    def total_amount(self) -> Decimal:
        return self.items_total + self.delivery_total

    @property
    def amount_to_pay(self) -> Decimal:
        """Итог минус бонусы: спишется с баланса или будет оплачено при получении."""
        return self.total_amount - self.bonus_amount


def shipment_key(method: DeliveryMethod, product: Product) -> tuple[int, int | None]:
    """
    Какие позиции едут одной отправкой (и платят за доставку один раз).
    Единственная точка этого правила: тарифы по весу, объединение магазинов
    логистикой маркета и т.п. меняются здесь.
    """
    if method.provider == DeliveryMethod.Provider.SHOP:
        return method.id, product.shop_id
    return method.id, None


def _build_plan(lines: list[CheckoutLine], choices: Iterable[DeliveryChoice]) -> CheckoutPlan:
    choices = list(choices)
    chosen = {choice.product_id: choice.delivery_method_id for choice in choices}
    if len(chosen) != len(choices):
        raise BusinessError("Товар указан несколько раз.", code="duplicate_product")

    buyable = {line.product.id: line for line in lines if line.can_buy}
    if set(chosen) != set(buyable):
        raise BusinessConflict("Корзина изменилась. Обновите страницу оформления.", code="cart_changed")

    shipments: dict[tuple, PlannedShipment] = {}
    for product_id, line in buyable.items():
        method = next((m for m in line.delivery_methods if m.id == chosen[product_id]), None)
        if method is None:
            raise BusinessError(
                f"Способ доставки недоступен для товара «{line.product.title}».",
                code="delivery_unavailable",
            )
        key = shipment_key(method, line.product)
        if key not in shipments:
            shop = line.product.shop if key[1] is not None else None
            shipments[key] = PlannedShipment(method=method, shop=shop)
        shipments[key].lines.append(line)

    return CheckoutPlan(lines=list(buyable.values()), shipments=list(shipments.values()))


def quote(
    cart: Cart | None, user: User | None, choices: Iterable[DeliveryChoice], use_bonus: bool = False
) -> CheckoutPlan:
    """Отправки и суммы для выбранных способов. Ничего не сохраняет. user=None — гость, без бонусов."""
    plan = _build_plan(_checkout_lines(cart), choices)
    if use_bonus and user is not None:
        plan = replace(plan, bonus_amount=payments.bonus_to_use(user, plan.total_amount))
    return plan


# --- Оформление ---


def _validate_slots(
    plan: CheckoutPlan, slots: Iterable[SlotChoice], now: datetime.datetime | None
) -> dict[int, DeliverySlot]:
    by_method: dict[int, SlotChoice] = {}
    for slot in slots:
        if slot.delivery_method_id in by_method:
            raise BusinessError("Время для способа доставки указано несколько раз.", code="duplicate_slot")
        by_method[slot.delivery_method_id] = slot

    result = {}
    methods = {shipment.method.id: shipment.method for shipment in plan.shipments}
    for method in methods.values():
        choice = by_method.get(method.id)
        slot = validate_slot(
            method,
            date=choice.date if choice else None,
            window_id=choice.window_id if choice else None,
            now=now,
        )
        if slot is not None:
            result[method.id] = slot
    return result


def _shipment_address(shipment: PlannedShipment, buyer_address: str) -> str:
    if shipment.method.needs_shop_address:
        return shipment.shop.address
    if shipment.method.requires_address:
        return buyer_address
    return ""


@transaction.atomic
def place_purchase(
    cart: Cart | None,
    user: User,
    *,
    choices: Iterable[DeliveryChoice],
    payment_method: str,
    expected_total: Decimal,
    slots: Iterable[SlotChoice] = (),
    address: str = "",
    comment: str = "",
    phone: str = "",
    use_bonus: bool = False,
    now: datetime.datetime | None = None,
) -> Purchase:
    """
    Оформляет покупку из корзины cart на покупателя user: заказы магазинов, отправки,
    списание остатков, оплата, удаление купленного из корзины. Всё в одной транзакции —
    любая ошибка (нет остатка, не хватает баланса, слот занят) откатывает всё целиком.

    expected_total — сумма, которую видел покупатель (итог до бонусов). Если корзина
    или цены успели измениться — BusinessConflict (409), покупатель должен проверить заново.
    phone — телефон для связи по заказу: указан — сохраняется в профиль покупателя.
    use_bonus — оплатить часть бонусами (см. orders.payments).
    """
    # Блокировки: корзина — повторное «Оформить» ждёт первое и видит уже пустую корзину;
    # затем товары в едином порядке (магазин, id), как и в create_order, — без дедлоков.
    if cart is not None:
        cart = Cart.objects.select_for_update().filter(pk=cart.pk).first()
    product_ids = list(CartItem.objects.filter(cart=cart).values_list("product_id", flat=True)) if cart else []
    list(Product.objects.select_for_update().filter(id__in=product_ids).order_by("shop_id", "id"))

    plan = _build_plan(_checkout_lines(cart), choices)
    slot_by_method = _validate_slots(plan, slots, now)

    address = address.strip()
    if not address and any(shipment.method.requires_address for shipment in plan.shipments):
        raise BusinessError("Укажите адрес доставки.", code="address_required")

    if plan.total_amount != expected_total:
        raise BusinessConflict(
            f"Сумма заказа изменилась: {plan.total_amount}. Проверьте заказ ещё раз.",
            code="total_changed",
        )

    purchase = Purchase.objects.create(
        buyer=user,
        payment_method=payment_method,
        items_total=plan.items_total,
        delivery_total=plan.delivery_total,
        total_amount=plan.total_amount,
        comment=comment.strip(),
    )

    # Заказ = магазин × отправка: у каждого заказа один способ доставки и свой путь статусов
    for planned in plan.shipments:
        slot = slot_by_method.get(planned.method.id)
        shipment = Shipment.objects.create(
            purchase=purchase,
            delivery_method=planned.method,
            shop=planned.shop,
            price=planned.price,
            address=_shipment_address(planned, address),
            slot_date=slot.date if slot else None,
            slot_start=slot.start if slot else None,
            slot_end=slot.end if slot else None,
        )
        lines_by_shop: dict[int, list[CheckoutLine]] = defaultdict(list)
        for line in planned.lines:
            lines_by_shop[line.product.shop_id].append(line)
        for shop_id in sorted(lines_by_shop):
            shop_lines = lines_by_shop[shop_id]
            create_order(
                buyer=user,
                shop=shop_lines[0].product.shop,
                purchase=purchase,
                shipment=shipment,
                lines=[OrderLine(line.product.id, line.quantity) for line in shop_lines],
            )

    payments.charge_purchase(purchase, use_bonus=use_bonus)

    CartItem.objects.filter(cart=cart, product_id__in=[line.product.id for line in plan.lines]).delete()
    if phone:
        update_profile(user, phone=phone)
    # «С этим товаром часто покупают»: сейчас или по cron — решает сама функция
    bought_together.on_purchase_placed(purchase)
    return purchase


@transaction.atomic
def place_guest_purchase(cart: Cart | None, *, account: User | None, email: str, password: str, **purchase) -> Purchase:
    """
    Гость оформляет покупку из своей корзины: в свой аккаунт (account — пароль уже проверен,
    см. users.serializers.CheckoutAccountSerializer) или в новый с этой почтой и паролем.
    Новый аккаунт создаётся в той же транзакции: покупка не оформилась — аккаунта нет.
    Войти в аккаунт после успеха — дело view (остаток корзины гостя перейдёт в корзину аккаунта).
    """
    buyer = account or register_user(email=email, password=password)
    return place_purchase(cart, buyer, **purchase)
