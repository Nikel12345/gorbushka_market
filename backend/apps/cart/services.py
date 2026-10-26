"""
Корзина. Все изменения — под блокировкой строки корзины (select_for_update),
поэтому параллельные «добавить» с двух вкладок не теряют количество и не
упираются в уникальность (cart, product).

Корзина есть и у гостя: Cart без пользователя, её id лежит в сессии (get_request_cart).
При входе гостевая корзина переливается в корзину пользователя (merge_guest_cart,
вызывается сигналом user_logged_in — для любого способа входа).

Правила:
- увеличить количество можно, только если товар на продаже и его хватает;
- уменьшить или убрать можно всегда (даже если товар уже снят с продажи);
- количество 0 = убрать позицию.
"""
import datetime
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Product
from apps.core.exceptions import BusinessError, BusinessNotFound

from .models import Cart, CartItem

MAX_CART_POSITIONS = 100
# Ключ сессии гостя с id его корзины. Данные сессии переживают вход (login меняет только ключ сессии)
GUEST_CART_SESSION_KEY = "guest_cart_id"


@dataclass(frozen=True)
class CartLine:
    item: CartItem

    @property
    def product(self) -> Product:
        return self.item.product

    @property
    def quantity(self) -> int:
        return self.item.quantity

    @property
    def available_quantity(self) -> int:
        """Сколько можно купить прямо сейчас."""
        if self.product.status != Product.Status.ACTIVE:
            return 0
        return self.product.quantity

    @property
    def is_available(self) -> bool:
        """Можно ли оформить позицию целиком в текущем количестве."""
        return 0 < self.quantity <= self.available_quantity

    @property
    def total(self) -> Decimal:
        return self.product.price * self.quantity


@dataclass(frozen=True)
class CartContent:
    lines: list[CartLine]

    @property
    def items_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def total_amount(self) -> Decimal:
        """Сумма только по доступным позициям — то, что реально можно оформить."""
        return sum((line.total for line in self.lines if line.is_available), Decimal("0.00"))

    @property
    def has_unavailable(self) -> bool:
        return any(not line.is_available for line in self.lines)


def get_request_cart(request, *, create: bool = False) -> Cart | None:
    """
    Корзина того, кто делает запрос: пользователя или гостя. Без create — None, если корзины ещё нет:
    пустую корзину в БД не создаём, пока в неё ничего не положили.
    """
    if request.user.is_authenticated:
        if create:
            return Cart.objects.get_or_create(user=request.user)[0]
        return Cart.objects.filter(user=request.user).first()

    cart_id = request.session.get(GUEST_CART_SESSION_KEY)
    cart = Cart.objects.filter(pk=cart_id, user=None).first() if cart_id else None
    if cart is None and create:
        cart = Cart.objects.create()
        request.session[GUEST_CART_SESSION_KEY] = cart.pk
    return cart


def get_cart(cart: Cart | None) -> CartContent:
    """Содержимое корзины одним запросом. Нет корзины — пустое."""
    if cart is None:
        return CartContent(lines=[])
    items = CartItem.objects.filter(cart=cart).select_related("product__shop").order_by("id")
    return CartContent(lines=[CartLine(item) for item in items])


def _locked(cart: Cart) -> Cart:
    return Cart.objects.select_for_update().get(pk=cart.pk)


def _ensure_can_buy(product_id: int, quantity: int) -> Product:
    product = Product.objects.on_sale().filter(pk=product_id).first()
    if product is None:
        raise BusinessError("Товар недоступен для покупки.", code="product_unavailable")
    if quantity > product.quantity:
        raise BusinessError(
            f"Недостаточно товара «{product.title}»: в наличии {product.quantity} шт.",
            code="insufficient_stock",
        )
    return product


@transaction.atomic
def add_item(cart: Cart, *, product_id: int, quantity: int = 1) -> None:
    """Положить товар в корзину. Если он уже там — количество увеличивается."""
    if quantity < 1:
        raise BusinessError("Количество должно быть не меньше 1.", code="invalid_quantity")

    cart = _locked(cart)
    item = cart.items.filter(product_id=product_id).first()

    if item is None and cart.items.count() >= MAX_CART_POSITIONS:
        raise BusinessError(f"В корзине может быть не больше {MAX_CART_POSITIONS} товаров.", code="cart_full")

    new_quantity = (item.quantity if item else 0) + quantity
    product = _ensure_can_buy(product_id, new_quantity)

    if item is None:
        CartItem.objects.create(cart=cart, product=product, quantity=new_quantity)
    else:
        item.quantity = new_quantity
        item.save(update_fields=["quantity", "updated_at"])


@transaction.atomic
def set_item_quantity(cart: Cart | None, *, product_id: int, quantity: int) -> None:
    """Задать количество товара в корзине. 0 — убрать товар."""
    if quantity < 0:
        raise BusinessError("Количество не может быть отрицательным.", code="invalid_quantity")

    item = _locked(cart).items.filter(product_id=product_id).first() if cart else None
    if item is None:
        raise BusinessNotFound("Этого товара нет в корзине.", code="not_in_cart")

    if quantity == 0:
        item.delete()
        return

    if quantity > item.quantity:
        _ensure_can_buy(product_id, quantity)

    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])


@transaction.atomic
def remove_item(cart: Cart | None, *, product_id: int) -> None:
    """Убрать товар из корзины. Повторное удаление — не ошибка."""
    if cart is not None:
        CartItem.objects.filter(cart=cart, product_id=product_id).delete()


@transaction.atomic
def clear_cart(cart: Cart | None) -> None:
    if cart is not None:
        CartItem.objects.filter(cart=cart).delete()


@transaction.atomic
def merge_guest_cart(guest_cart_id: int, user) -> None:
    """
    Гость вошёл или зарегистрировался: его товары переходят в корзину пользователя,
    одинаковые — складываются. Остаток и лимит позиций не проверяем: лишнее корзина
    покажет недоступным, как товар, который закончился, пока лежал в корзине.
    """
    guest = Cart.objects.select_for_update().filter(pk=guest_cart_id, user=None).first()
    if guest is None:
        return
    guest_items = list(guest.items.all())
    if guest_items:
        cart = _locked(Cart.objects.get_or_create(user=user)[0])
        own = {item.product_id: item for item in cart.items.all()}
        for item in guest_items:
            if item.product_id in own:
                own_item = own[item.product_id]
                own_item.quantity += item.quantity
                own_item.save(update_fields=["quantity", "updated_at"])
            else:
                item.cart = cart
                item.save(update_fields=["cart", "updated_at"])
    guest.delete()


def delete_stale_guest_carts() -> int:
    """Корзины гостей, которых не меняли дольше жизни сессии: сессия истекла, до корзины уже не добраться."""
    cutoff = timezone.now() - datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE)
    stale = Cart.objects.filter(user=None, updated_at__lt=cutoff).exclude(items__updated_at__gte=cutoff)
    ids = list(stale.values_list("pk", flat=True))
    Cart.objects.filter(pk__in=ids).delete()
    return len(ids)
