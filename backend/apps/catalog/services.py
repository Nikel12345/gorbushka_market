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
) -> Product:
    return Product.objects.create(
        shop=shop,
        title=title,
        description=description,
        price=price,
        quantity=quantity,
    )


def archive_product(product: Product) -> Product:
    """Снимает товар с продажи («удаление» из кабинета). История заказов сохраняется."""
    product.status = Product.Status.ARCHIVED
    product.save(update_fields=["status", "updated_at"])
    return product
