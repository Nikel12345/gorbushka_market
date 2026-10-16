from collections.abc import Sequence
from decimal import Decimal

from django.conf import settings
from django.db import transaction

from apps.core.exceptions import BusinessError
from apps.core.files import delete_file_on_commit
from apps.shops.models import Shop

from .models import Product, ProductImage


@transaction.atomic
def create_product(
    *,
    shop: Shop,
    title: str,
    price: Decimal,
    quantity: int = 1,
    description: str = "",
    image=None,
    images: Sequence = (),
    delivery_methods=(),
) -> Product:
    """image — обложка (старое поле, совместимость), images — остальные фото по порядку."""
    product = Product.objects.create(
        shop=shop,
        title=title,
        description=description,
        price=price,
        quantity=quantity,
    )
    product.delivery_methods.set(delivery_methods)
    files = [image, *images] if image else list(images)
    if files:
        add_images(product, files)
    return product


@transaction.atomic
def update_product(product: Product, **fields) -> Product:
    """
    Частичное изменение товара. delivery_methods — заменить набор способов доставки.
    images — добавить фото в конец. image — старое поле одной картинки: файл заменяет
    обложку, None убирает её (обложкой станет следующее фото).
    Цены в уже оформленных заказах не меняются: там снимок.
    """
    delivery_methods = fields.pop("delivery_methods", None)
    images = fields.pop("images", None)
    has_cover, cover = "image" in fields, fields.pop("image", None)

    if fields:
        for name, value in fields.items():
            setattr(product, name, value)
        product.save(update_fields=[*fields, "updated_at"])
    if delivery_methods is not None:
        product.delivery_methods.set(delivery_methods)
    if has_cover:
        replace_cover(product, cover)
    if images:
        add_images(product, images)
    return product


def archive_product(product: Product) -> Product:
    """Снимает товар с продажи («удаление» из кабинета). История заказов сохраняется."""
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=["status", "updated_at"])
    return product


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
