import datetime
from decimal import Decimal

from django.db import migrations

# Стартовый справочник. Дальше способы и условия правятся в админке.
METHODS = [
    {
        "code": "pickup",
        "name": "Самовывоз из павильона",
        "kind": "pickup",
        "provider": "shop",
        "price": Decimal("0.00"),
        "requires_address": False,
        "eta_min_days": None,
        "eta_max_days": None,
        "slot_days_ahead": 0,
        "sort_order": 10,
        "windows": [],
    },
    {
        "code": "market_courier",
        "name": "Курьер маркета",
        "kind": "courier",
        "provider": "market",
        "price": Decimal("50.00"),
        "requires_address": True,
        "eta_min_days": 1,
        "eta_max_days": 2,
        "slot_days_ahead": 7,
        "sort_order": 20,
        "windows": [(10, 14), (14, 18), (18, 22)],
    },
]


def seed(apps, schema_editor):
    DeliveryMethod = apps.get_model("delivery", "DeliveryMethod")
    DeliveryTimeWindow = apps.get_model("delivery", "DeliveryTimeWindow")

    for data in METHODS:
        data = dict(data)
        windows = data.pop("windows")
        method, _ = DeliveryMethod.objects.update_or_create(code=data.pop("code"), defaults=data)
        for start, end in windows:
            DeliveryTimeWindow.objects.get_or_create(
                method=method,
                start_time=datetime.time(start),
                end_time=datetime.time(end),
            )


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
