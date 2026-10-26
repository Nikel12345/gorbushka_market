from django.core.management.base import BaseCommand

from apps.cart import services


class Command(BaseCommand):
    help = "Удалить брошенные корзины гостей — нетронутые дольше срока жизни сессии (для ночного cron)."

    def handle(self, *args, **options):
        count = services.delete_stale_guest_carts()
        self.stdout.write(f"Удалено корзин гостей: {count}")
