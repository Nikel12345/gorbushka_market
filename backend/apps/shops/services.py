from .models import Shop


def update_shop(shop: Shop, **fields) -> Shop:
    for name, value in fields.items():
        setattr(shop, name, value)
    shop.save(update_fields=[*fields, "updated_at"])
    return shop
