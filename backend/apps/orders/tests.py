from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.core.exceptions import BusinessError
from apps.shops.models import Shop
from apps.users.models import User

from .models import Order
from .services import OrderLine, create_order


class OrderFixturesMixin:
    def setUp(self):
        self.seller = User.objects.create_user(email="seller@example.com", password="x")
        self.buyer = User.objects.create_user(email="buyer@example.com", password="x", first_name="Анна")
        self.shop = Shop.objects.create(owner=self.seller, name="Павильон 12")
        self.phone = Product.objects.create(shop=self.shop, title="iPhone 15", price=Decimal("1000.00"), quantity=5)
        self.case = Product.objects.create(shop=self.shop, title="Чехол", price=Decimal("150.50"), quantity=10)


class CreateOrderServiceTests(OrderFixturesMixin, TestCase):
    def test_creates_order_with_snapshot_and_decrements_stock(self):
        order = create_order(
            buyer=self.buyer,
            shop=self.shop,
            lines=[OrderLine(self.phone.id, 2), OrderLine(self.case.id, 1)],
        )

        self.assertEqual(order.total_amount, Decimal("2150.50"))
        self.assertEqual(order.status, Order.Status.NEW)
        items = {item.product_id: item for item in order.items.all()}
        self.assertEqual(items[self.phone.id].title, "iPhone 15")
        self.assertEqual(items[self.phone.id].price, Decimal("1000.00"))
        self.assertEqual(items[self.phone.id].quantity, 2)
        self.phone.refresh_from_db()
        self.case.refresh_from_db()
        self.assertEqual(self.phone.quantity, 3)
        self.assertEqual(self.case.quantity, 9)

    def test_duplicate_lines_are_merged(self):
        order = create_order(
            buyer=self.buyer,
            shop=self.shop,
            lines=[OrderLine(self.phone.id, 1), OrderLine(self.phone.id, 2)],
        )

        self.assertEqual(order.items.get().quantity, 3)

    def test_history_is_not_affected_by_product_changes(self):
        order = create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.phone.id, 1)])

        self.phone.title = "iPhone 15 (уценка)"
        self.phone.price = Decimal("500.00")
        self.phone.save()

        item = order.items.get()
        self.assertEqual(item.title, "iPhone 15")
        self.assertEqual(item.price, Decimal("1000.00"))

    def test_insufficient_stock_rolls_back_everything(self):
        with self.assertRaises(BusinessError) as ctx:
            create_order(
                buyer=self.buyer,
                shop=self.shop,
                lines=[OrderLine(self.case.id, 1), OrderLine(self.phone.id, 6)],
            )

        self.assertEqual(ctx.exception.code, "insufficient_stock")
        self.assertFalse(Order.objects.exists())
        self.case.refresh_from_db()
        self.phone.refresh_from_db()
        self.assertEqual(self.case.quantity, 10)
        self.assertEqual(self.phone.quantity, 5)

    def test_archived_product_cannot_be_ordered(self):
        self.phone.status = Product.Status.ARCHIVED
        self.phone.save()

        with self.assertRaises(BusinessError) as ctx:
            create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.phone.id, 1)])

        self.assertEqual(ctx.exception.code, "product_unavailable")

    def test_product_from_another_shop_cannot_be_ordered(self):
        other_shop = Shop.objects.create(owner=self.seller, name="Другой")

        with self.assertRaises(BusinessError) as ctx:
            create_order(buyer=self.buyer, shop=other_shop, lines=[OrderLine(self.phone.id, 1)])

        self.assertEqual(ctx.exception.code, "product_unavailable")

    def test_empty_and_invalid_quantities(self):
        with self.assertRaises(BusinessError):
            create_order(buyer=self.buyer, shop=self.shop, lines=[])
        with self.assertRaises(BusinessError):
            create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.phone.id, 0)])


class SellerOrderHistoryTests(OrderFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.seller)
        self.url = reverse("seller-order-list", args=[self.shop.id])

    def test_lists_shop_orders_newest_first_with_items(self):
        first = create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.phone.id, 1)])
        second = create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.case.id, 2)])

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        results = response.data["results"]
        self.assertEqual([o["id"] for o in results], [second.id, first.id])
        self.assertEqual(results[0]["total_amount"], "301.00")
        self.assertEqual(results[0]["status"], "new")
        self.assertEqual(results[0]["buyer"]["email"], "buyer@example.com")
        self.assertEqual(
            results[0]["items"],
            [
                {
                    "id": second.items.get().id,
                    "product_id": self.case.id,
                    "title": "Чехол",
                    "price": "150.50",
                    "quantity": 2,
                    "total": "301.00",
                }
            ],
        )

    def test_does_not_include_other_shops_orders(self):
        other_seller = User.objects.create_user(email="other@example.com", password="x")
        other_shop = Shop.objects.create(owner=other_seller, name="Чужой")
        other_product = Product.objects.create(shop=other_shop, title="Y", price=Decimal("1"), quantity=1)
        create_order(buyer=self.buyer, shop=other_shop, lines=[OrderLine(other_product.id, 1)])

        response = self.client.get(self.url)

        self.assertEqual(response.data["count"], 0)

    def test_filter_by_status(self):
        new = create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.phone.id, 1)])
        done = create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.phone.id, 1)])
        done.status = Order.Status.COMPLETED
        done.save()

        response = self.client.get(self.url, {"status": "new"})

        self.assertEqual([o["id"] for o in response.data["results"]], [new.id])

    def test_invalid_status_filter_is_400(self):
        response = self.client.get(self.url, {"status": "lost"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_foreign_shop_is_404(self):
        other_seller = User.objects.create_user(email="other@example.com", password="x")
        other_shop = Shop.objects.create(owner=other_seller, name="Чужой")

        response = self.client.get(reverse("seller-order-list", args=[other_shop.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_buyer_cannot_see_shop_history(self):
        self.client.force_login(self.buyer)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_query_count_does_not_grow_with_orders(self):
        for _ in range(5):
            create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.case.id, 1)])

        # сессия + пользователь + магазин + count + заказы с покупателем + позиции
        with self.assertNumQueries(6):
            self.client.get(self.url)


class AdminPagesTests(OrderFixturesMixin, TestCase):
    def test_admin_pages_render(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="x")
        order = create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.phone.id, 1)])
        self.client.force_login(admin)

        for url in [
            reverse("admin:shops_shop_changelist"),
            reverse("admin:shops_shop_change", args=[self.shop.id]),
            reverse("admin:catalog_product_changelist"),
            reverse("admin:catalog_product_change", args=[self.phone.id]),
            reverse("admin:orders_order_changelist"),
            reverse("admin:orders_order_change", args=[order.id]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        self.assertEqual(self.client.get(reverse("admin:orders_order_add")).status_code, 403)


class BuyerOrderHistoryTests(OrderFixturesMixin, APITestCase):
    url = reverse("me-order-list")

    def setUp(self):
        super().setUp()
        self.client.force_login(self.buyer)
        self.other_shop = Shop.objects.create(owner=self.seller, name="Павильон 40")
        self.other_product = Product.objects.create(
            shop=self.other_shop, title="Наушники", price=Decimal("300"), quantity=10
        )

    def order(self, shop=None, product=None, quantity=1, buyer=None, created_at=None, status_=None):
        order = create_order(
            buyer=buyer or self.buyer,
            shop=shop or self.shop,
            lines=[OrderLine((product or self.case).id, quantity)],
        )
        updates = {}
        if created_at:
            updates["created_at"] = created_at
        if status_:
            updates["status"] = status_
        if updates:
            Order.objects.filter(pk=order.pk).update(**updates)
            order.refresh_from_db()
        return order

    def ids(self, response):
        return [o["id"] for o in response.data["results"]]

    def fetch_all(self, params=None):
        ids, cursor = [], None
        while True:
            query = {**(params or {}), "page_size": 2, **({"cursor": cursor} if cursor else {})}
            response = self.client.get(self.url, query)
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            ids += self.ids(response)
            cursor = response.data["next_cursor"]
            if cursor is None:
                return ids

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_only_own_orders_with_shop_and_items(self):
        own = self.order()
        stranger = User.objects.create_user(email="stranger@example.com", password="x")
        self.order(buyer=stranger)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.ids(response), [own.id])
        data = response.data["results"][0]
        self.assertEqual(data["shop"], {"id": self.shop.id, "name": "Павильон 12"})
        self.assertEqual(data["items"][0]["title"], "Чехол")
        self.assertNotIn("buyer", data)

    def test_cursor_walk_newest_first(self):
        orders = [self.order() for _ in range(5)]

        self.assertEqual(self.fetch_all(), [o.id for o in reversed(orders)])

    def test_sort_by_total_with_cursor(self):
        small = self.order(quantity=1)  # 150.50
        big = self.order(product=self.phone, quantity=1)  # 1000
        mid = self.order(quantity=2)  # 301

        self.assertEqual(self.fetch_all({"sort": "total_desc"}), [big.id, mid.id, small.id])
        self.assertEqual(self.fetch_all({"sort": "total_asc"}), [small.id, mid.id, big.id])

    def test_filter_by_several_statuses(self):
        new = self.order()
        confirmed = self.order(status_=Order.Status.CONFIRMED)
        self.order(status_=Order.Status.CANCELLED)

        response = self.client.get(self.url, {"status": ["new", "confirmed"]})

        self.assertEqual(set(self.ids(response)), {new.id, confirmed.id})

    def test_filter_by_shop(self):
        self.order()
        other = self.order(shop=self.other_shop, product=self.other_product)

        self.assertEqual(self.ids(self.client.get(self.url, {"shop": self.other_shop.id})), [other.id])

    def test_filter_by_date_range(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        msk = ZoneInfo("Europe/Moscow")
        self.order(created_at=datetime(2026, 1, 31, 23, 59, tzinfo=msk))
        inside = [
            self.order(created_at=datetime(2026, 2, 1, 0, 0, tzinfo=msk)),
            self.order(created_at=datetime(2026, 2, 28, 23, 59, tzinfo=msk)),
        ]
        self.order(created_at=datetime(2026, 3, 1, 0, 0, tzinfo=msk))

        response = self.client.get(self.url, {"date_from": "2026-02-01", "date_to": "2026-02-28"})

        self.assertEqual(set(self.ids(response)), {o.id for o in inside})

    def test_filters_and_cursor_combined(self):
        expected = [self.order(shop=self.other_shop, product=self.other_product) for _ in range(3)]
        for _ in range(3):
            self.order()

        self.assertEqual(self.fetch_all({"shop": self.other_shop.id}), [o.id for o in reversed(expected)])

    def test_invalid_filters_are_400(self):
        for params in [
            {"status": "lost"},
            {"date_from": "not-a-date"},
            {"date_from": "2026-03-01", "date_to": "2026-02-01"},
            {"sort": "random"},
            {"cursor": "garbage"},
        ]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url, params).status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_count_does_not_grow(self):
        for _ in range(10):
            self.order()

        # сессия + пользователь + заказы (с магазином и покупателем) + позиции
        with self.assertNumQueries(4):
            self.client.get(self.url, {"page_size": 50})


class SharedOrderFilterTests(OrderFixturesMixin, APITestCase):
    """Кабинет продавца использует тот же OrderFilter, что и страница покупателя."""

    def test_seller_history_supports_same_filters(self):
        self.client.force_login(self.seller)
        url = reverse("seller-order-list", args=[self.shop.id])
        new = create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.case.id, 1)])
        done = create_order(buyer=self.buyer, shop=self.shop, lines=[OrderLine(self.case.id, 1)])
        Order.objects.filter(pk=done.pk).update(status=Order.Status.COMPLETED)

        response = self.client.get(url, {"status": ["new", "completed"], "date_from": "2000-01-01"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({o["id"] for o in response.data["results"]}, {new.id, done.id})
        # постраничный формат кабинета не изменился
        self.assertIn("count", response.data)
