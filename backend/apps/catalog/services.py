from collections.abc import Sequence
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from apps.core.exceptions import BusinessError
from apps.core.files import delete_file_on_commit
from apps.shops.models import Shop

from . import variants
from .categories import check_parent
from .models import (
    Category,
    Characteristic,
    CharacteristicValue,
    Product,
    ProductCharacteristic,
    ProductGroup,
    ProductImage,
)


@transaction.atomic
def create_product(
    *,
    shop: Shop,
    title: str,
    price_usd: Decimal,
    quantity: int = 1,
    description: str = "",
    category: Category | None = None,
    image=None,
    images: Sequence = (),
    delivery_methods=(),
    group: ProductGroup | None = None,
    characteristic_values: Sequence[CharacteristicValue] = (),
) -> Product:
    """
    image — обложка (старое поле, совместимость), images — остальные фото по порядку.
    group и characteristic_values — группа вариантов и значения характеристик (catalog/variants.py).
    """
    product = Product.objects.create(
        shop=shop,
        title=title,
        description=description,
        category=category,
        price_usd=price_usd,
        quantity=quantity,
        group=group,
    )
    product.delivery_methods.set(delivery_methods)
    if group is not None or characteristic_values:
        _lock_group(group)
        variants.check_variant(product, characteristic_values)
        _set_characteristics(product, characteristic_values)
    files = [image, *images] if image else list(images)
    if files:
        add_images(product, files)
    return product


@transaction.atomic
def update_product(product: Product, **fields) -> Product:
    """
    Частичное изменение товара. delivery_methods — заменить набор способов доставки.
    characteristic_values — заменить значения характеристик; они, категория и группа
    проверяются по правилам вариантов (catalog/variants.py).
    images — добавить фото в конец. image — старое поле одной картинки: файл заменяет
    обложку, None убирает её (обложкой станет следующее фото).
    Цены в уже оформленных заказах не меняются: там снимок.
    """
    delivery_methods = fields.pop("delivery_methods", None)
    characteristic_values = fields.pop("characteristic_values", None)
    images = fields.pop("images", None)
    has_cover, cover = "image" in fields, fields.pop("image", None)

    for name, value in fields.items():
        setattr(product, name, value)
    if {"category", "group"} & fields.keys() or characteristic_values is not None:
        values = characteristic_values
        if values is None:
            values = [row.value for row in product.characteristics.select_related("value__characteristic")]
        _lock_group(product.group)
        variants.check_variant(product, values)
    if characteristic_values is not None:
        _set_characteristics(product, characteristic_values)
    if fields:
        product.save(update_fields=[*fields, "updated_at"])
    if delivery_methods is not None:
        product.delivery_methods.set(delivery_methods)
    if has_cover:
        replace_cover(product, cover)
    if images:
        add_images(product, images)
    return product


def _lock_group(group: ProductGroup | None) -> None:
    """Изменения товаров одной группы и её осей идут по очереди: иначе два одинаковых варианта пройдут проверку."""
    if group is not None:
        ProductGroup.objects.select_for_update().get(pk=group.pk)


def _set_characteristics(product: Product, values: Sequence[CharacteristicValue]) -> None:
    product.characteristics.all().delete()
    ProductCharacteristic.objects.bulk_create(
        ProductCharacteristic(product=product, characteristic_id=value.characteristic_id, value=value)
        for value in values
    )
    # Товар мог прийти с prefetch — иначе в ответе останутся старые значения
    getattr(product, "_prefetched_objects_cache", {}).pop("characteristics", None)


def archive_product(product: Product) -> Product:
    """Снимает товар с продажи («удаление» в админке магазина). История заказов сохраняется."""
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=["status", "updated_at"])
    return product


# --- Категории ---


def create_category(*, name: str, parent: Category | None = None, **fields) -> Category:
    """slug не передан — генерируется из названия (Category.save)."""
    return Category.objects.create(name=name, parent=parent, **fields)


def update_category(category: Category, **fields) -> Category:
    """parent — перенос: разрешён куда угодно, кроме самой категории и её подкатегорий."""
    if "parent" in fields:
        check_parent(category, fields["parent"])
    for name, value in fields.items():
        setattr(category, name, value)
    category.save(update_fields=[*fields, "updated_at"])
    return category


@transaction.atomic
def delete_category(category: Category) -> None:
    """
    Только пустую: без подкатегорий, характеристик, групп и товаров на продаже. Снятые с продажи товары
    остаются без категории — их уже не видно ни в каталоге, ни в админке магазина.
    """
    Category.objects.select_for_update().get(pk=category.pk)
    if category.children.exists():
        raise BusinessError("В категории есть подкатегории — сначала перенесите или удалите их.", code="category_not_empty")
    if category.characteristics.exists():
        raise BusinessError(
            "К категории привязаны характеристики — сначала привяжите их к другой категории.",
            code="category_not_empty",
        )
    if category.product_groups.exists():
        raise BusinessError(
            "К категории привязаны группы вариантов — сначала привяжите их к другой категории.",
            code="category_not_empty",
        )
    on_sale = category.products.filter(status=Product.Status.ACTIVE).count()
    if on_sale:
        raise BusinessError(
            f"В категории товары на продаже ({on_sale}) — сначала перенесите их в другую категорию.",
            code="category_not_empty",
        )
    category.products.update(category=None)
    category.delete()


# --- Характеристики ---


def update_characteristic(characteristic: Characteristic, **fields) -> Characteristic:
    """
    category — перенос в другую ветку: не проверяется, как и перенос категорий. Товары, где
    характеристика стала недоступна, перестают её показывать (catalog/variants.py).
    """
    for name, value in fields.items():
        setattr(characteristic, name, value)
    characteristic.save(update_fields=list(fields))
    return characteristic


# --- Группы вариантов ---


@transaction.atomic
def create_group(*, name: str, axes: Sequence[Characteristic], category: Category | None = None) -> ProductGroup:
    group = ProductGroup(name=name, category=category)
    variants.check_group(group, axes)
    group.save()
    group.axes.set(axes)
    return group


@transaction.atomic
def update_group(group: ProductGroup, *, axes: Sequence[Characteristic] | None = None, **fields) -> ProductGroup:
    """
    axes — новый набор осей, category — новая категория. Проверяются по правилам вариантов
    (catalog/variants.py): оси доступны в категории, товары группы на продаже — в ней,
    со значениями всех осей и без повторов.
    """
    for name, value in fields.items():
        setattr(group, name, value)
    if axes is not None or "category" in fields:
        _lock_group(group)
        variants.check_group(group, axes if axes is not None else list(group.axes.all()))
    if fields:
        group.save(update_fields=[*fields, "updated_at"])
    if axes is not None:
        group.axes.set(axes)
        getattr(group, "_prefetched_objects_cache", {}).pop("axes", None)
    return group


# --- Фото ---
# Все изменения фото идут под блокировкой товара: параллельные загрузки не превысят
# лимит и не перепутают порядок, а обложка всегда совпадает с первым фото.


def _forget_prefetched_images(product: Product) -> None:
    # Товар мог прийти с prefetch_related("images") — иначе прочитаем и отдадим старый список
    getattr(product, "_prefetched_objects_cache", {}).pop("images", None)


def _lock(product: Product) -> None:
    Product.objects.select_for_update().get(pk=product.pk)
    _forget_prefetched_images(product)


def sync_cover(product: Product) -> None:
    """Выставляет Product.image по первому фото. Вызывать после любого изменения фото."""
    _forget_prefetched_images(product)
    first = product.images.order_by("position", "id").values_list("image", flat=True).first()
    cover = first or ""
    if product.image.name != cover:
        product.image = cover
        product.save(update_fields=["image", "updated_at"])


@transaction.atomic
def add_images(product: Product, files: Sequence) -> list[ProductImage]:
    """Добавляет фото в конец. Больше PRODUCT_IMAGES_MAX — ошибка, ничего не сохраняется."""
    _lock(product)
    existing = list(product.images.values_list("position", flat=True))
    limit = settings.PRODUCT_IMAGES_MAX
    if len(existing) + len(files) > limit:
        raise BusinessError(f"У товара может быть не больше {limit} фото.", code="too_many_images")

    start = max(existing, default=-1) + 1
    created = [
        ProductImage.objects.create(product=product, image=file, position=start + offset)
        for offset, file in enumerate(files)
    ]
    sync_cover(product)
    return created


@transaction.atomic
def delete_image(image: ProductImage) -> None:
    """Файл удаляется после коммита (catalog/signals.py)."""
    product = image.product
    _lock(product)
    image.delete()
    sync_cover(product)


@transaction.atomic
def reorder_images(product: Product, ids: Sequence[int]) -> list[ProductImage]:
    """ids — все фото товара в новом порядке, первое станет обложкой."""
    _lock(product)
    images = {image.id: image for image in product.images.all()}
    if len(ids) != len(set(ids)) or set(ids) != set(images):
        raise BusinessError(
            "Передайте все фото товара, каждое один раз. Возможно, список фото изменился — обновите его.",
            code="image_order_mismatch",
        )

    ordered = [images[image_id] for image_id in ids]
    for position, image in enumerate(ordered):
        image.position = position
    ProductImage.objects.bulk_update(ordered, ["position"])
    sync_cover(product)
    return ordered


@transaction.atomic
def replace_cover(product: Product, file) -> None:
    """
    Старое поле `image` (одна картинка): файл заменяет первое фото или добавляется,
    если фото нет; None удаляет первое фото.
    """
    _lock(product)
    cover = product.images.order_by("position", "id").first()
    if file is None:
        if cover:
            cover.delete()
    elif cover is None:
        ProductImage.objects.create(product=product, image=file, position=0)
    else:
        delete_file_on_commit(cover.image)
        cover.image = file
        cover.save(update_fields=["image"])
    sync_cover(product)
