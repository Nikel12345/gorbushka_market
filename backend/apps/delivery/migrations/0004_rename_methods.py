"""
Интернет-магазин вместо рынка: названия засеянных способов доставки без «павильона» и «маркета».
Меняется только название, которое ещё не правили в админке.
"""
from django.db import migrations

RENAMES = {
    "pickup": ("Самовывоз из павильона", "Самовывоз из магазина"),
    "market_courier": ("Курьер маркета", "Доставка курьером"),
}


def rename(apps, forward):
    DeliveryMethod = apps.get_model("delivery", "DeliveryMethod")
    for code, (old, new) in RENAMES.items():
        current, target = (old, new) if forward else (new, old)
        DeliveryMethod.objects.filter(code=code, name=current).update(name=target)


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0003_rename_labels"),
    ]

    operations = [
        migrations.RunPython(lambda apps, _: rename(apps, True), lambda apps, _: rename(apps, False)),
    ]
