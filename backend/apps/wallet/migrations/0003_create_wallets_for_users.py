from django.conf import settings
from django.db import migrations


def create_wallets(apps, schema_editor):
    """Кошелёк создаётся вместе с пользователем — заводим его и уже существующим."""
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Wallet = apps.get_model("wallet", "Wallet")
    Wallet.objects.bulk_create(
        [Wallet(user_id=user_id) for user_id in User.objects.filter(wallet__isnull=True).values_list("id", flat=True)]
    )


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0002_buckets_operations'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_wallets, migrations.RunPython.noop),
    ]
