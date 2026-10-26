"""
«Рекомендуем» в корзине: сначала аксессуары товаров корзины (catalog/accessories.py), потом лента
главной — одной бесконечной лентой (pagination.CartRecommendationsPagination).

Аксессуары идут по очереди от каждого товара корзины, в порядке корзины: первые аксессуары всех
товаров, затем вторые и т.д. — так наверху самые важные для каждого товара, а не все аксессуары
первого. Повторы и сами товары корзины не предлагаем. Варианты товаров корзины (другой цвет того же
телефона) убираем только из ленты: в аксессуарах их выбрал менеджер — белый геймпад к приставке нужен
и тогда, когда красный уже в корзине. Учитываются только товары корзины на продаже.

Список считается заново на каждый запрос порции: если корзина изменилась во время прокрутки, лента
может сдвинуться — фронт загружает её заново при входе в корзину.
"""
from dataclasses import dataclass

from django.db.models import Q, QuerySet

from apps.cart.models import Cart, CartItem
from apps.catalog.models import Product, ProductAccessory


@dataclass(frozen=True)
class CartRecommendations:
    # id аксессуаров товаров корзины по порядку показа (на продаже)
    leading: list[int]
    # Лента главной без них, без товаров корзины и их вариантов
    rest: QuerySet[Product]


def cart_recommendations(cart: Cart | None) -> CartRecommendations:
    in_cart: list[tuple[int, int | None]] = []
    if cart is not None:
        in_cart = list(
            CartItem.objects.filter(cart=cart, product__status=Product.Status.ACTIVE)
            .order_by("id")
            .values_list("product_id", "product__group_id")
        )
    product_ids = {product_id for product_id, _ in in_cart}
    group_ids = {group_id for _, group_id in in_cart if group_id is not None}

    leading = _accessories(in_cart, product_ids, group_ids)
    rest = (
        Product.objects.on_sale()
        .exclude(pk__in=product_ids | set(leading))
        .exclude(group_id__in=group_ids)
        .select_related("shop")
    )
    return CartRecommendations(leading=leading, rest=rest)


def _accessories(in_cart: list[tuple[int, int | None]], product_ids: set[int], group_ids: set[int]) -> list[int]:
    # Модель товара — группа вариантов или сам товар без группы; два цвета одного телефона — одна модель
    models = list(dict.fromkeys(("group", group_id) if group_id else ("product", pk) for pk, group_id in in_cart))
    if not models:
        return []
    links = (
        ProductAccessory.objects.filter(
            Q(group_id__in=group_ids) | Q(product_id__in=[pk for kind, pk in models if kind == "product"]),
            accessory__status=Product.Status.ACTIVE,
        )
        .exclude(accessory_id__in=product_ids)
        .order_by("position", "id")
        .values_list("group_id", "product_id", "accessory_id", "accessory__group_id")
    )
    by_model: dict[tuple[str, int], list[int]] = {}
    for group_id, product_id, accessory_id, accessory_group_id in links:
        if group_id is not None and accessory_group_id == group_id:
            continue  # вошёл в группу уже после того, как стал её аксессуаром — как на странице товара
        key = ("group", group_id) if group_id is not None else ("product", product_id)
        by_model.setdefault(key, []).append(accessory_id)

    lists = [by_model.get(model, []) for model in models]
    ordered = (accessories[rank] for rank in range(max(map(len, lists))) for accessories in lists if rank < len(accessories))
    return list(dict.fromkeys(ordered))
