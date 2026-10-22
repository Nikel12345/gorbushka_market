from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Product, ProductGroup
from apps.orders.models import Order, OrderItem, Purchase
from apps.orders.test_checkout import CheckoutFixturesMixin
from apps.shops.models import Shop
from apps.users.models import User

from . import services
from .models import BoughtTogether


class BoughtTogetherBase(APITestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Магазин", address="Адрес")
        self.buyer = User.objects.create_user(email="buyer@example.com", password="x")
        self.phone = self.make("Телефон")
        self.case = self.make("Чехол")
        self.charger = self.make("Зарядка")
        self.glass = self.make("Стекло")

    def make(self, title, **kwargs):
        return Product.objects.create(shop=self.shop, title=title, price_usd=Decimal("100"), **kwargs)

    def buy(self, *products, split=False, cancelled=False):
        """Покупка с товарами; split — каждый товар отдельным заказом (разные способы доставки)."""
        purchase = Purchase.objects.create(
            buyer=self.buyer, payment_method="on_delivery", items_total=0, delivery_total=0, total_amount=0
        )
        for group in [[product] for product in products] if split else [products]:
            order = Order.objects.create(
                shop=self.shop,
                buyer=self.buyer,
                purchase=purchase,
                total_amount=0,
                status=Order.Status.CANCELLED if cancelled else Order.Status.NEW,
            )
            for product in group:
                OrderItem.objects.create(order=order, product=product, title=product.title, price=product.price, quantity=1)
        return purchase

    def top(self, product):
        return [(row.related.title, row.purchases_count) for row in product.bought_together.order_by("position")]


class TopTests(BoughtTogetherBase):
    def test_top_by_joint_purchases(self):
        self.buy(self.phone, self.case, self.charger)
        self.buy(self.phone, self.case, self.glass)
        self.buy(self.phone, self.case, self.charger)
        self.buy(self.case, self.glass)  # без телефона — топу телефона не важна

        services.refresh_products([self.phone.id, self.case.id])

        self.assertEqual(self.top(self.phone), [("Чехол", 3), ("Зарядка", 2), ("Стекло", 1)])
        self.assertEqual(self.top(self.case), [("Телефон", 3), ("Стекло", 2), ("Зарядка", 2)])

    def test_purchase_split_into_orders_counts_as_one(self):
        self.buy(self.phone, self.case, split=True)

        services.refresh_products([self.phone.id])

        self.assertEqual(self.top(self.phone), [("Чехол", 1)])

    def test_only_top_size_latest_first_on_tie(self):
        extras = [self.make(f"Товар {index}") for index in range(services.TOP_SIZE + 2)]
        for extra in extras:
            self.buy(self.phone, extra)

        services.refresh_products([self.phone.id])

        expected = [(extra.title, 1) for extra in reversed(extras)][: services.TOP_SIZE]
        self.assertEqual(self.top(self.phone), expected)

    def test_skips_cancelled_off_sale_and_same_group(self):
        group = ProductGroup.objects.create(name="Телефон")
        self.phone.group = group
        self.phone.save()
        blue_phone = self.make("Телефон синий", group=group)
        archived = self.make("Снят с продажи", status=Product.Status.ARCHIVED)
        self.buy(self.phone, self.case, cancelled=True)
        self.buy(self.phone, blue_phone, archived, self.charger)

        services.refresh_products([self.phone.id])

        self.assertEqual(self.top(self.phone), [("Зарядка", 1)])

    def test_variants_share_top(self):
        group = ProductGroup.objects.create(name="Телефон")
        Product.objects.filter(pk=self.phone.pk).update(group=group)
        never_bought = self.make("Телефон синий", group=group)
        archived = self.make("Телефон красный", group=group, status=Product.Status.ARCHIVED)
        self.buy(self.phone, self.case)
        self.buy(self.phone, self.case, self.charger)

        services.refresh_products([self.phone.id])

        expected = [("Чехол", 2), ("Зарядка", 1)]
        self.assertEqual(self.top(self.phone), expected)
        self.assertEqual(self.top(never_bought), expected)
        self.assertEqual(self.top(archived), [])

    def test_related_group_takes_one_place(self):
        group = ProductGroup.objects.create(name="Геймпад")
        black = self.make("Геймпад чёрный", group=group)
        white = self.make("Геймпад белый", group=group)
        red = self.make("Геймпад красный", group=group)
        self.buy(self.phone, black, white)  # два цвета в одной покупке — одна покупка
        self.buy(self.phone, white)
        self.buy(self.phone, red)

        services.refresh_products([self.phone.id])
        self.assertEqual(self.top(self.phone), [("Геймпад белый", 3)])  # чаще всех покупали вместе

        Product.objects.filter(pk=white.pk).update(quantity=0)
        Product.objects.filter(pk=red.pk).update(status=Product.Status.ARCHIVED)
        services.refresh_products([self.phone.id])
        self.assertEqual(self.top(self.phone), [("Геймпад чёрный", 3)])  # в наличии и на продаже

    @mock.patch.object(services, "_CHECK_BATCH", 2)
    def test_off_sale_skipped_across_batches(self):
        self.buy(self.phone, self.case)
        for index in range(3):  # куплены позже чехла — в кандидатах выше него
            self.buy(self.phone, self.make(f"Снят {index}", status=Product.Status.ARCHIVED))

        services.refresh_products([self.phone.id])

        self.assertEqual(self.top(self.phone), [("Чехол", 1)])

    def test_refresh_replaces_old_top_and_clears_off_sale(self):
        self.buy(self.phone, self.case)
        services.refresh_products([self.phone.id, self.case.id])
        self.buy(self.phone, self.charger)
        self.buy(self.phone, self.charger)
        self.case.status = Product.Status.ARCHIVED
        self.case.save()

        services.refresh_products([self.phone.id, self.case.id])

        self.assertEqual(self.top(self.phone), [("Зарядка", 2)])
        self.assertEqual(self.top(self.case), [])

    def test_refresh_all_command(self):
        self.buy(self.phone, self.case)
        BoughtTogether.objects.create(product=self.glass, related=self.charger, purchases_count=9, position=1)

        output = StringIO()
        call_command("refresh_bought_together", stdout=output)

        self.assertEqual(self.top(self.phone), [("Чехол", 1)])
        self.assertEqual(self.top(self.case), [("Телефон", 1)])
        self.assertEqual(self.top(self.glass), [])  # покупок со стеклом нет — устаревший топ стёрт
        self.assertIn("Пересчитано товаров: 3", output.getvalue())


class OnPurchaseTests(CheckoutFixturesMixin, APITestCase):
    def place(self, *products):
        self.to_cart(*products)
        total = sum(product.price for product in products)
        return self.checkout(self.choose(*[(product, self.pickup) for product in products]), str(total))

    def test_checkout_refreshes_products_of_purchase(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.place(self.phone, self.case)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(list(self.phone.bought_together.values_list("related__title", flat=True)), ["Чехол"])
        self.assertEqual(list(self.case.bought_together.values_list("related__title", flat=True)), ["iPhone 15"])

    @override_settings(BOUGHT_TOGETHER_ON_PURCHASE=False)
    def test_daily_mode_does_not_refresh_on_checkout(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.place(self.phone, self.case)

        self.assertFalse(BoughtTogether.objects.exists())
        self.assertEqual(callbacks, [])


class BoughtTogetherApiTests(BoughtTogetherBase):
    def url(self, product):
        return reverse("product-bought-together", args=[product.id])

    def test_cards_in_top_order_on_sale_only(self):
        self.buy(self.phone, self.case, self.charger)
        self.buy(self.phone, self.case)
        services.refresh_products([self.phone.id])
        self.case.status = Product.Status.ARCHIVED  # сняли после пересчёта
        self.case.save()

        response = self.client.get(self.url(self.phone))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([card["title"] for card in response.data], ["Зарядка"])
        self.assertIn("in_stock", response.data[0])

    def test_empty_without_purchases(self):
        response = self.client.get(self.url(self.phone))

        self.assertEqual(response.data, [])

    def test_off_sale_product_404(self):
        self.phone.status = Product.Status.ARCHIVED
        self.phone.save()

        self.assertEqual(self.client.get(self.url(self.phone)).status_code, status.HTTP_404_NOT_FOUND)

    def test_two_queries(self):
        self.buy(self.phone, self.case, self.charger, self.glass)
        services.refresh_products([self.phone.id])

        with self.assertNumQueries(2):  # товар на продаже, карточки топа с магазином
            self.client.get(self.url(self.phone))
