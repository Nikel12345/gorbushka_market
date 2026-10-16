from django.db import migrations


def move_shipment_to_order(apps, schema_editor):
    """Заказ = магазин × отправка: отправка переезжает с позиций на заказ."""
    Order = apps.get_model("orders", "Order")
    for order in Order.objects.filter(shipment__isnull=True):
        item = order.items.exclude(shipment__isnull=True).order_by("id").first()
        if item is not None:
            order.shipment_id = item.shipment_id
            order.save(update_fields=["shipment"])


class Migration(migrations.Migration):
    """Отдельно от 0004: перенос данных и смена схемы в одной транзакции ломаются на PostgreSQL."""

    dependencies = [
        ("orders", "0004_order_shipment_statuses"),
    ]

    operations = [
        migrations.RunPython(move_shipment_to_order, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="orderitem",
            name="shipment",
        ),
    ]
