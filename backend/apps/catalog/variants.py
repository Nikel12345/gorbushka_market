"""
Варианты товара — товары одной группы (ProductGroup), которые различаются значениями
характеристик-осей группы (ProductGroup.axes): цвет, память. Каждый вариант — отдельный
товар со своей страницей, ценой и остатком. Связей между товарами нигде не хранится:
кнопки вариантов строятся по товарам группы при каждом запросе (variant_options).

Правила (проверяются здесь; вызывают сервисы и админка Django):
- у товара одно значение каждой характеристики, и все его характеристики доступны в его
  категории (Characteristic.category);
- оси группы доступны в категории группы (ProductGroup.category), а её товары лежат в этой
  категории или её подкатегориях;
- у товара в группе есть значения всех осей группы;
- у товаров группы на продаже наборы значений осей не повторяются.
Снятые с продажи товары в вариантах не участвуют.

Перенос категорий и характеристик ничего не проверяет. Если после него товар оказался вне
категории группы или ось стала недоступна в его категории, вариантов у товара не видно
(variant_options), пока данные не поправят в админке.
"""
from collections.abc import Callable, Iterable, Sequence

from apps.core.exceptions import BusinessError

from .categories import CategoryTree
from .models import Characteristic, CharacteristicValue, Product, ProductCharacteristic, ProductGroup


def check_characteristics(values: Iterable[CharacteristicValue]) -> None:
    seen = set()
    for value in values:
        if value.characteristic_id in seen:
            raise BusinessError(
                f"У характеристики «{value.characteristic}» выберите одно значение.",
                code="characteristic_repeated",
            )
        seen.add(value.characteristic_id)


def check_variant(product: Product, values: Sequence[CharacteristicValue]) -> None:
    """
    values — все значения характеристик товара после изменения. Категория, группа и статус
    берутся из product (он может быть ещё не сохранён — админка Django проверяет до сохранения).
    """
    check_characteristics(values)
    group = product.group if product.status == Product.Status.ACTIVE else None
    tree = None
    if any(value.characteristic.category_id for value in values) or (group and group.category_id):
        tree = CategoryTree.load()
    _check_in_category(product, values, tree)
    if group is None:
        return
    if group.category_id is not None and product.category_id not in tree.subtree_ids(group.category_id):
        raise BusinessError(
            f"Товары группы «{group}» лежат в категории «{group.category}» и её подкатегориях.",
            code="variant_product_outside_category",
        )

    axes = list(group.axes.all())
    chosen = {value.characteristic_id: value.id for value in values}
    missing = [axis.name for axis in axes if axis.id not in chosen]
    if missing:
        raise BusinessError(
            f"Товару в группе «{group}» нужно указать: {', '.join(missing)}.",
            code="variant_axis_missing",
        )

    key = _key(chosen, axes)
    for other_id, combo in _combos(group, exclude_product_id=product.pk).items():
        if _key(combo, axes) == key:
            title = Product.objects.values_list("title", flat=True).get(pk=other_id)
            raise BusinessError(
                f"В группе «{group}» уже есть товар с такими значениями: «{title}».",
                code="variant_duplicate",
            )


def _check_in_category(product: Product, values: Sequence[CharacteristicValue], tree: CategoryTree | None) -> None:
    """tree — None, если ни одна характеристика не привязана к категории: проверять нечего."""
    if tree is None:
        return
    foreign = [value.characteristic.name for value in values if not tree.allows(value.characteristic, product.category_id)]
    if foreign:
        where = f"категории «{product.category}»" if product.category_id else "товара без категории"
        raise BusinessError(
            f"Не подходят для {where}: {', '.join(foreign)}.",
            code="characteristic_not_in_category",
        )


def check_group(group: ProductGroup, axes: Sequence[Characteristic]) -> None:
    """
    Группа с новыми осями axes и/или новой категорией (уже в group.category): оси доступны
    в категории группы, а все её товары на продаже лежат в этой категории, заполнили все оси
    и не повторяются.
    """
    if not axes:
        raise BusinessError(
            "Укажите хотя бы одну характеристику, по которой различаются варианты.",
            code="variant_axes_required",
        )
    tree = None
    if group.category_id is not None or any(axis.category_id for axis in axes):
        tree = CategoryTree.load()
        foreign = [axis.name for axis in axes if not tree.allows(axis, group.category_id)]
        if foreign:
            where = f"категории «{group.category}»" if group.category_id else "группы без категории"
            raise BusinessError(f"Не подходят для {where}: {', '.join(foreign)}.", code="variant_axis_not_in_category")
    if group.pk is None:
        return

    inside = tree.subtree_ids(group.category_id) if group.category_id is not None else None
    combos = _combos(group)
    seen: dict[tuple, str] = {}
    products = Product.objects.on_sale().filter(group=group).values_list("id", "title", "category_id")
    for product_id, title, category_id in products:
        if inside is not None and category_id not in inside:
            raise BusinessError(
                f"Товар «{title}» лежит вне категории «{group.category}».",
                code="variant_product_outside_category",
            )
        combo = combos.get(product_id, {})
        missing = [axis.name for axis in axes if axis.id not in combo]
        if missing:
            raise BusinessError(f"У товара «{title}» не указано: {', '.join(missing)}.", code="variant_axis_missing")
        key = _key(combo, axes)
        if key in seen:
            raise BusinessError(
                f"Товары «{seen[key]}» и «{title}» не различаются по {', '.join(axis.name for axis in axes)}.",
                code="variant_duplicate",
            )
        seen[key] = title


def variant_options(product: Product, get_tree: Callable[[], CategoryTree] = CategoryTree.load) -> list[dict]:
    """
    Кнопки вариантов на странице товара: строка на каждую ось группы, в ней — значения,
    которые есть у товаров группы на продаже. Кнопка ведёт на товар с этим значением и
    остальными осями как у текущего. Если такого нет — на ближайший (больше совпадающих
    осей, при равенстве — совпадают более ранние оси), и у кнопки exact=False.

    Товары вне категории группы или с недоступной в их категории осью в вариантах не участвуют;
    если это сам товар — вариантов у него нет. get_tree — дерево категорий (нужно, только
    если группа или оси привязаны к категориям).
    """
    if product.group_id is None:
        return []

    group = product.group
    axes = list(group.axes.all())
    siblings = list(Product.objects.on_sale().filter(group_id=group.id).order_by("id").with_characteristics())
    if group.category_id is not None or any(axis.category_id is not None for axis in axes):
        tree = get_tree()
        inside = tree.subtree_ids(group.category_id) if group.category_id is not None else None

        def fits(category_id):
            if inside is not None and category_id not in inside:
                return False
            return all(tree.allows(axis, category_id) for axis in axes)

        if not fits(product.category_id):
            return []
        siblings = [sibling for sibling in siblings if fits(sibling.category_id)]
    combos: dict[int, dict[int, int]] = {}
    values: dict[int, CharacteristicValue] = {}
    for sibling in siblings:
        combos[sibling.id] = {row.characteristic_id: row.value_id for row in sibling.characteristics.all()}
        values.update((row.value_id, row.value) for row in sibling.characteristics.all())
    current = combos.get(product.id) or {row.characteristic_id: row.value_id for row in product.characteristics.all()}

    def matches(sibling, wanted):
        return [combos[sibling.id].get(axis.id) == wanted.get(axis.id) for axis in axes]

    rows = []
    for axis in axes:
        axis_values = {combo[axis.id] for combo in combos.values() if axis.id in combo}
        options = []
        for value_id in sorted(axis_values, key=lambda pk: (values[pk].sort_order, pk)):
            wanted = {**current, axis.id: value_id}
            candidates = [sibling for sibling in siblings if combos[sibling.id].get(axis.id) == value_id]
            target = max(candidates, key=lambda sibling: (sum(matches(sibling, wanted)), matches(sibling, wanted)))
            options.append(
                {
                    "value_id": value_id,
                    "value": values[value_id].value,
                    "product_id": target.id,
                    "selected": value_id == current.get(axis.id),
                    "exact": all(matches(target, wanted)),
                    "in_stock": target.quantity > 0,
                }
            )
        rows.append({"characteristic_id": axis.id, "name": axis.name, "options": options})
    return rows


def _key(combo: dict[int, int], axes: Sequence[Characteristic]) -> tuple:
    return tuple(combo.get(axis.id) for axis in axes)


def _combos(group: ProductGroup, *, exclude_product_id: int | None = None) -> dict[int, dict[int, int]]:
    """Значения характеристик товаров группы на продаже: {product_id: {characteristic_id: value_id}}."""
    rows = ProductCharacteristic.objects.filter(product__group=group, product__status=Product.Status.ACTIVE)
    if exclude_product_id is not None:
        rows = rows.exclude(product_id=exclude_product_id)
    combos: dict[int, dict[int, int]] = {}
    for product_id, characteristic_id, value_id in rows.values_list("product_id", "characteristic_id", "value_id"):
        combos.setdefault(product_id, {})[characteristic_id] = value_id
    return combos
