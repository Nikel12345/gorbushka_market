from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.db import transaction

from apps.catalog.models import Product
from apps.core.exceptions import BusinessError
from apps.shops.models import Shop

from .models import Order, OrderItem


@dataclass(frozen=True)
class OrderLine:
    product_id: int
    quantity: int


@transaction.atomic
def create_order(*, buyer, shop: Shop, lines: Iterable[OrderLine]) -> Order:
    """
    Оформляет заказ в магазине: фиксирует цены, списывает остатки.
    Всё в одной транзакции — либо заказ создан и остатки списаны, либо ничего.
    """
    quantities: Counter[int] = Counter()
    for line in lines:
        if line.quantity < 1:
            raise BusinessError("Количество товара должно быть положительным.", code="invalid_quantity")
        quantities[line.product_id] += line.quantity

    if not quantities:
        raise BusinessError("Заказ не может быть пустым.", code="empty_order")

    # Блокируем строки товаров до конца транзакции, чтобы параллельные заказы
    # не продали один и тот же остаток дважды. Сортировка по id — защита от дедлоков.
    # (SQLite блокирует всю БД на запись, select_for_update там игнорируется.)
    products = {
        product.id: product
        for product in Product.objects.select_for_update()
        .filter(id__in=quantities, shop=shop)
        .on_sale()
        .order_by("id")
    }

    unavailable = sorted(set(quantities) - set(products))
    if unavailable:
        raise BusinessError(
            f"Товары недоступны для заказа в этом магазине: {unavailable}.",
            code="product_unavailable",
        )

    for product_id, quantity in quantities.items():
        product = products[product_id]
        if product.quantity < quantity:
            raise BusinessError(
                f"Недостаточно товара «{product.title}»: в наличии {product.quantity}.",
                code="insufficient_stock",
            )

    total = sum(
        (products[product_id].price * quantity for product_id, quantity in quantities.items()),
        Decimal("0"),
    )
    order = Order.objects.create(shop=shop, buyer=buyer, total_amount=total)

    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            product=products[product_id],
            title=products[product_id].title,
            price=products[product_id].price,
            quantity=quantity,
        )
        for product_id, quantity in quantities.items()
    )

    for product_id, quantity in quantities.items():
        product = products[product_id]
        product.quantity -= quantity
        product.save(update_fields=["quantity", "updated_at"])

    return order
