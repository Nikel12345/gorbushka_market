from decimal import Decimal

from django.db import transaction

from apps.shops.models import Shop

from .models import Product


@transaction.atomic
def create_product(
    *,
    shop: Shop,
    title: str,
    price: Decimal,
    quantity: int = 1,
    description: str = "",
    image=None,
    delivery_methods=(),
) -> Product:
    product = Product.objects.create(
        shop=shop,
        title=title,
        description=description,
        price=price,
        quantity=quantity,
        image=image or "",
    )
    product.delivery_methods.set(delivery_methods)
    return product


@transaction.atomic
def update_product(product: Product, **fields) -> Product:
    """
    Частичное изменение товара. image=None — убрать картинку,
    delivery_methods — заменить набор способов доставки.
    Цены в уже оформленных заказах не меняются: там снимок.
    """
    delivery_methods = fields.pop("delivery_methods", None)
    old_image_name = product.image.name if "image" in fields else None

    if "image" in fields and fields["image"] is None:
        fields["image"] = ""

    for name, value in fields.items():
        setattr(product, name, value)
    product.save(update_fields=[*fields, "updated_at"])
    if delivery_methods is not None:
        product.delivery_methods.set(delivery_methods)

    # Старый файл удаляем только после успешного коммита: при откате он ещё нужен
    if old_image_name and old_image_name != product.image.name:
        storage = product.image.storage
        transaction.on_commit(lambda: storage.delete(old_image_name))

    return product


def archive_product(product: Product) -> Product:
    """Снимает товар с продажи («удаление» из кабинета). История заказов сохраняется."""
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=["status", "updated_at"])
    return product
