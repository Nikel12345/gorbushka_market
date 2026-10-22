from django.core.management.base import BaseCommand

from apps.recommendations import services


class Command(BaseCommand):
    help = "Пересчитать «С этим товаром часто покупают» для всех товаров (для ночного cron)."

    def handle(self, *args, **options):
        count = services.refresh_all()
        self.stdout.write(f"Пересчитано товаров: {count}")
