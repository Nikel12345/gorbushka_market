"""
Цены товаров теперь в долларах: price → price_usd. Прежние рублёвые цены переводятся
по курсу ЦБ на 21.10.2026 (тот же, что засеян в currency/0001), так что на витрине они почти не меняются.
"""
from decimal import ROUND_HALF_UP, Decimal

import django.core.validators
from django.db import migrations, models

RUB_PER_USD = Decimal("82.8879")
CENT = Decimal("0.01")


def rub_to_usd(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    products = list(Product.objects.only("id", "price_usd"))
    for product in products:
        product.price_usd = max((product.price_usd / RUB_PER_USD).quantize(CENT, ROUND_HALF_UP), CENT)
    Product.objects.bulk_update(products, ["price_usd"], batch_size=500)


def usd_to_rub(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    products = list(Product.objects.only("id", "price_usd"))
    for product in products:
        product.price_usd = (product.price_usd * RUB_PER_USD).quantize(CENT, ROUND_HALF_UP)
    Product.objects.bulk_update(products, ["price_usd"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0010_product_rating_product_reviews_count"),
        ("currency", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="product", name="catalog_product_price_positive"),
        migrations.RemoveIndex(model_name="product", name="catalog_feed_price_idx"),
        migrations.RenameField(model_name="product", old_name="price", new_name="price_usd"),
        migrations.AlterField(
            model_name="product",
            name="price_usd",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(Decimal("0.01"))],
                verbose_name="цена, $",
            ),
        ),
        migrations.RunPython(rub_to_usd, usd_to_rub),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["status", "price_usd", "id"], name="catalog_feed_price_idx"),
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.CheckConstraint(
                condition=models.Q(price_usd__gt=0), name="catalog_product_price_positive"
            ),
        ),
    ]
