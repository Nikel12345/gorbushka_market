"""
Корзина. Все изменения — под блокировкой строки корзины (select_for_update),
поэтому параллельные «добавить» с двух вкладок не теряют количество и не
упираются в уникальность (cart, product).

Правила:
- увеличить количество можно, только если товар на продаже и его хватает;
- уменьшить или убрать можно всегда (даже если товар уже снят с продажи);
- количество 0 = убрать позицию.
"""
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from apps.catalog.models import Product
from apps.core.exceptions import BusinessError, BusinessNotFound

from .models import Cart, CartItem

MAX_CART_POSITIONS = 100


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


def get_cart(user) -> CartContent:
    """Содержимое корзины одним запросом. Пустую корзину в БД не создаём."""
    items = CartItem.objects.filter(cart__user=user).select_related("product__shop").order_by("id")
    return CartContent(lines=[CartLine(item) for item in items])


def _locked_cart(user) -> Cart:
    Cart.objects.get_or_create(user=user)
    return Cart.objects.select_for_update().get(user=user)


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
def add_item(user, *, product_id: int, quantity: int = 1) -> None:
    """Положить товар в корзину. Если он уже там — количество увеличивается."""
    if quantity < 1:
        raise BusinessError("Количество должно быть не меньше 1.", code="invalid_quantity")

    cart = _locked_cart(user)
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
def set_item_quantity(user, *, product_id: int, quantity: int) -> None:
    """Задать количество товара в корзине. 0 — убрать товар."""
    if quantity < 0:
        raise BusinessError("Количество не может быть отрицательным.", code="invalid_quantity")

    cart = _locked_cart(user)
    item = cart.items.filter(product_id=product_id).first()
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
def remove_item(user, *, product_id: int) -> None:
    """Убрать товар из корзины. Повторное удаление — не ошибка."""
    CartItem.objects.filter(cart__user=user, product_id=product_id).delete()


@transaction.atomic
def clear_cart(user) -> None:
    CartItem.objects.filter(cart__user=user).delete()
