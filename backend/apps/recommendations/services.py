"""
«С этим товаром часто покупают».

Считается по моделям, а не по отдельным вариантам: товар группы вариантов (catalog/variants.py)
— это вся группа, «iPhone 16 Pro» в любом цвете и объёме. Поэтому:
- у всех вариантов группы топ общий — и у тех, что ещё ни разу не покупали;
- в топе группа другого товара занимает одно место: покупка с чёрным и белым DualSense
  считается один раз, а показывается вариант, который чаще покупали вместе (на продаже,
  по возможности в наличии);
- другие варианты самого товара в топ не попадают — к чёрному iPhone не предлагаем синий.
Товар без группы — сам себе модель.

Для каждого товара хранится только топ из TOP_SIZE товаров, которые чаще всего оказывались
с ним в одной покупке (Purchase — всё, что оформлено одной кнопкой, даже если покупка
разделилась на заказы по способам доставки). При равенстве выше тот, с кем покупали позже.
Отменённые заказы и товары не на продаже не считаются.

Пересчёт читает только покупки с этой моделью, а не все заказы (см. _top).

Когда пересчитывать — решает on_purchase_placed (её вызывает оформление покупки):
- сейчас, BOUGHT_TOGETHER_ON_PURCHASE=True — сразу после покупки, только её модели:
  совместные покупки остальных от неё не меняются;
- раз в сутки — BOUGHT_TOGETHER_ON_PURCHASE=False и cron на
  `python manage.py refresh_bought_together` (refresh_all — все товары).
Отмена заказа топ сразу не меняет: до следующей покупки этих товаров или ночного пересчёта.
"""
from collections import defaultdict
from typing import Iterable

from django.conf import settings
from django.db import transaction
from django.db.models import Case, Count, Max, When

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem, Purchase

from .models import BoughtTogether

TOP_SIZE = 5
# Сколько мест-кандидатов проверять на «на продаже» за один запрос
_CHECK_BATCH = 50


def on_purchase_placed(purchase: Purchase) -> None:
    if not settings.BOUGHT_TOGETHER_ON_PURCHASE:
        return
    product_ids = list(
        OrderItem.objects.filter(order__purchase=purchase).values_list("product_id", flat=True).distinct()
    )
    if len(product_ids) < 2:
        return  # один товар — новых пар нет
    # После коммита: покупка уже оформлена, и ошибка пересчёта её не откатит (robust — только в лог)
    transaction.on_commit(lambda: refresh_products(product_ids), robust=True)


def refresh_products(product_ids: Iterable[int]) -> None:
    """Пересчитывает топ товаров вместе со всеми вариантами их групп; у снятых с продажи — очищает."""
    models: set[tuple[str, int]] = set()
    for pk, group_id in Product.objects.filter(pk__in=product_ids).values_list("pk", "group_id"):
        models.add(("group", group_id) if group_id is not None else ("product", pk))
    for kind, pk in sorted(models):
        variant_ids = (
            list(Product.objects.filter(group_id=pk).values_list("pk", flat=True)) if kind == "group" else [pk]
        )
        _refresh_model(variant_ids)


def refresh_all() -> int:
    """Пересчитывает топ всех купленных товаров и чистит устаревший. Возвращает число пересчитанных товаров."""
    product_ids = set(OrderItem.objects.filter(order__purchase__isnull=False).values_list("product_id", flat=True))
    product_ids |= set(BoughtTogether.objects.values_list("product_id", flat=True))
    refresh_products(product_ids)
    return len(product_ids)


@transaction.atomic
def _refresh_model(variant_ids: list[int]) -> None:
    # Два пересчёта одной модели (две покупки разом) идут по очереди
    variants = list(Product.objects.select_for_update().filter(pk__in=variant_ids).order_by("pk"))
    BoughtTogether.objects.filter(product__in=variants).delete()
    top = _top(variant_ids)
    BoughtTogether.objects.bulk_create(
        BoughtTogether(product=variant, related_id=related_id, purchases_count=purchases, position=position)
        for variant in variants
        if variant.status == Product.Status.ACTIVE
        for position, (related_id, purchases) in enumerate(top, start=1)
    )


def _top(variant_ids: list[int]) -> list[tuple[int, int]]:
    """Топ модели из вариантов variant_ids: [(id товара для показа, совместных покупок)]."""
    # Только покупки с моделью: по индексам позиции модели → её покупки → их заказы → их позиции.
    # Условий на таблицу товаров в WHERE нет (она нужна только ради group_id) — иначе база может
    # начать с неё и перебрать позиции всех заказов; «на продаже» проверяется ниже, пачками.
    counted = OrderItem.objects.filter(order__purchase__isnull=False).exclude(order__status=Order.Status.CANCELLED)
    together = counted.filter(
        order__purchase_id__in=counted.filter(product_id__in=variant_ids).values("order__purchase_id")
    ).exclude(product_id__in=variant_ids)
    stats = {"purchases": Count("order__purchase_id", distinct=True), "last_purchase": Max("order__purchase_id")}

    # Места топа: группа вариантов целиком (group_id) или товар без группы (single_id)
    places = list(
        together.values("product__group_id", single_id=Case(When(product__group__isnull=True, then="product_id")))
        .annotate(**stats)
        .order_by("-purchases", "-last_purchase")
    )
    # Варианты групп — от самого частого в совместных покупках
    variants_by_group = defaultdict(list)
    for row in together.values("product_id", "product__group_id").annotate(**stats).order_by("-purchases", "-last_purchase"):
        if row["product__group_id"] is not None:
            variants_by_group[row["product__group_id"]].append(row["product_id"])

    def candidates(place) -> list[int]:
        return [place["single_id"]] if place["single_id"] is not None else variants_by_group[place["product__group_id"]]

    top = []
    for start in range(0, len(places), _CHECK_BATCH):
        batch = places[start : start + _CHECK_BATCH]
        on_sale = dict(
            Product.objects.on_sale()
            .filter(pk__in=[pk for place in batch for pk in candidates(place)])
            .values_list("pk", "quantity")
        )
        for place in batch:
            choices = [pk for pk in candidates(place) if pk in on_sale]
            if choices:
                in_stock = [pk for pk in choices if on_sale[pk] > 0]
                top.append(((in_stock or choices)[0], place["purchases"]))
        if len(top) >= TOP_SIZE:
            break
    return top[:TOP_SIZE]
