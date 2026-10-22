"""
Маркетплейс → интернет-магазин: магазин остаётся один — главный (с наименьшим id).
Товары, заказы, отправки самовывоза и реклама остальных магазинов переходят в него,
остальные магазины удаляются. На новой установке магазина нет — его заводят в админке.
"""
from django.db import migrations


def merge_into_single_shop(apps, schema_editor):
    Shop = apps.get_model("shops", "Shop")
    main = Shop.objects.order_by("id").first()
    if main is None:
        return
    others = Shop.objects.exclude(pk=main.pk)
    if not others.exists():
        return

    # Реклама удаляется каскадом вместе с магазином — её тоже переносим
    for model in ("catalog.Product", "orders.Order", "orders.Shipment", "promo.Promo"):
        apps.get_model(model).objects.filter(shop__in=others).update(shop=main)
    others.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("shops", "0002_shop_address"),
        ("catalog", "0005_product_images"),
        ("orders", "0007_admin_actor"),
        ("promo", "0002_shop_link"),
    ]

    operations = [
        migrations.RunPython(merge_into_single_shop, migrations.RunPython.noop),
    ]
