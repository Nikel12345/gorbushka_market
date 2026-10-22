import datetime
from decimal import Decimal

from django.db import migrations, models

# Курс ЦБ на 21.10.2026: по нему переведены в доллары прежние рублёвые цены (catalog/0011).
# Он же — запасной курс, пока сервер ни разу не получил свежий от ЦБ
INITIAL_DATE = datetime.date(2026, 10, 21)
INITIAL_USD_RATE = Decimal("82.8879")


def seed_rate(apps, schema_editor):
    ExchangeRate = apps.get_model("currency", "ExchangeRate")
    ExchangeRate.objects.get_or_create(currency="USD", date=INITIAL_DATE, defaults={"rate": INITIAL_USD_RATE})


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ExchangeRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("currency", models.CharField(default="USD", max_length=3, verbose_name="валюта")),
                ("date", models.DateField(verbose_name="дата курса")),
                ("rate", models.DecimalField(decimal_places=4, max_digits=12, verbose_name="рублей за 1 единицу")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="получен")),
            ],
            options={
                "verbose_name": "курс валюты",
                "verbose_name_plural": "курсы валют",
                "ordering": ["-date", "currency"],
                "constraints": [
                    models.UniqueConstraint(fields=("currency", "date"), name="currency_rate_unique_date"),
                    models.CheckConstraint(condition=models.Q(rate__gt=0), name="currency_rate_positive"),
                ],
            },
        ),
        migrations.RunPython(seed_rate, migrations.RunPython.noop),
    ]
