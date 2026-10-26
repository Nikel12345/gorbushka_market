"""
Аксессуары — товары, которые предлагаем к модели товара в разделе «Аксессуары» на его странице:
чехлы, стёкла, зарядки. Список составляет менеджер, порядок — его.

Задаются модели, а не варианту (как и «Часто покупают», apps/recommendations): у товара группы
вариантов (catalog/variants.py) список общий для всей группы — и у новых её вариантов тоже;
у товара без группы — свой. Аксессуар — конкретный товар (вариант), его и показываем.

Правила при записи (check_accessories): аксессуар — не сам товар и не вариант той же группы,
без повторов, не больше PRODUCT_ACCESSORIES_MAX. На витрине — только аксессуары на продаже:
снятые скрыты (и вернутся, если товар вернут в продажу).

Смена группы у товара аксессуаров не теряет (services.keep_accessories_on_group_change):
товар без группы вошёл в группу — его аксессуары добавляются в конец списка группы;
вышел из группы — получает копию её списка.
"""
from collections.abc import Sequence

from django.conf import settings
from django.db.models import QuerySet

from apps.core.exceptions import BusinessError

from .models import Product, ProductAccessory


def links_of(product: Product) -> QuerySet[ProductAccessory]:
    """Строки списка модели товара: группы, если товар в группе, иначе его собственные."""
    if product.group_id is not None:
        return ProductAccessory.objects.filter(group_id=product.group_id)
    return ProductAccessory.objects.filter(product_id=product.pk)


def accessories_of(product: Product) -> QuerySet[Product]:
    """Аксессуары товара на продаже по порядку списка."""
    owner = (
        {"accessory_for__group_id": product.group_id}
        if product.group_id is not None
        else {"accessory_for__product_id": product.pk}
    )
    accessories = Product.objects.on_sale().filter(**owner).exclude(pk=product.pk)
    if product.group_id is not None:
        # Товар мог войти в группу уже после того, как его добавили к ней аксессуаром
        accessories = accessories.exclude(group_id=product.group_id)
    return accessories.order_by("accessory_for__position", "accessory_for__id")


def check_accessories(accessories: Sequence[Product], *, group_id: int | None, product_id: int | None) -> None:
    """
    accessories — новый список модели: группы group_id или товара product_id без группы
    (у ещё не сохранённого товара — None).
    """
    limit = settings.PRODUCT_ACCESSORIES_MAX
    if len(accessories) > limit:
        raise BusinessError(f"У товара может быть не больше {limit} аксессуаров.", code="too_many_accessories")
    if len({accessory.pk for accessory in accessories}) != len(accessories):
        raise BusinessError("Аксессуар в списке повторяется.", code="accessory_repeated")
    for accessory in accessories:
        if (product_id is not None and accessory.pk == product_id) or (
            group_id is not None and accessory.group_id == group_id
        ):
            raise BusinessError(
                f"«{accessory}» — вариант этого же товара, аксессуаром он быть не может.",
                code="accessory_same_model",
            )
