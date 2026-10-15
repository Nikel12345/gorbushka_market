from django.db import transaction

from .models import Shop


@transaction.atomic
def create_shop(*, owner, name: str, description: str = "") -> Shop:
    return Shop.objects.create(owner=owner, name=name, description=description)


def update_shop(shop: Shop, **fields) -> Shop:
    for name, value in fields.items():
        setattr(shop, name, value)
    shop.save(update_fields=[*fields, "updated_at"])
    return shop
