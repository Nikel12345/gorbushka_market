import base64
import json
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.shops.models import Shop
from apps.users.models import User

from .models import Product


class SellerProductTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="seller@example.com", password="x")
        self.other = User.objects.create_user(email="other@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.user, name="Павильон 12")
        self.foreign_shop = Shop.objects.create(owner=self.other, name="Чужой")
        self.client.force_login(self.user)

    def list_url(self, shop=None):
        return reverse("seller-product-list", args=[(shop or self.shop).id])

    def detail_url(self, product, shop=None):
        return reverse("seller-product-detail", args=[(shop or self.shop).id, product.id])

    def make_product(self, shop=None, **kwargs):
        defaults = {"title": "iPhone 15", "price": Decimal("79990.00"), "quantity": 3}
        return Product.objects.create(shop=shop or self.shop, **{**defaults, **kwargs})

    # --- create ---

    def test_create_product(self):
        response = self.client.post(
            self.list_url(),
            {"title": "iPhone 15", "description": "128 ГБ", "price": "79990.00", "quantity": 3},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.shop, self.shop)
        self.assertEqual(product.price, Decimal("79990.00"))
        self.assertEqual(product.status, Product.Status.ACTIVE)
        self.assertEqual(response.data["price"], "79990.00")
        self.assertEqual(response.data["status"], "active")

    def test_create_ignores_status_and_shop_from_request(self):
        response = self.client.post(
            self.list_url(),
            {"title": "X", "price": "10", "status": "archived", "shop": self.foreign_shop.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.shop, self.shop)
        self.assertEqual(product.status, Product.Status.ACTIVE)

    def test_create_validates_price_and_quantity(self):
        response = self.client.post(
            self.list_url(),
            {"title": "X", "price": "0", "quantity": -1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price", response.data)
        self.assertIn("quantity", response.data)

    def test_create_in_foreign_shop_is_404(self):
        response = self.client.post(
            self.list_url(self.foreign_shop),
            {"title": "X", "price": "10"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Product.objects.exists())

    def test_requires_authentication(self):
        self.client.logout()

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- list ---

    def test_list_returns_only_active_products_of_shop(self):
        active = self.make_product(title="Активный")
        self.make_product(title="Удалённый", status=Product.Status.ARCHIVED)
        self.make_product(shop=self.foreign_shop, title="Чужой")

        response = self.client.get(self.list_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual([p["id"] for p in response.data["results"]], [active.id])

    def test_list_foreign_shop_is_404(self):
        response = self.client.get(self.list_url(self.foreign_shop))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- delete ---

    def test_delete_archives_product(self):
        product = self.make_product()

        response = self.client.delete(self.detail_url(product))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        product.refresh_from_db()
        self.assertEqual(product.status, Product.Status.ARCHIVED)
        self.assertEqual(self.client.get(self.list_url()).data["count"], 0)

    def test_delete_twice_is_404(self):
        product = self.make_product()
        self.client.delete(self.detail_url(product))

        response = self.client.delete(self.detail_url(product))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_foreign_product_is_404(self):
        foreign = self.make_product(shop=self.foreign_shop)

        # и через чужой магазин, и подставив чужой товар в свой магазин
        responses = [
            self.client.delete(self.detail_url(foreign, shop=self.foreign_shop)),
            self.client.delete(self.detail_url(foreign, shop=self.shop)),
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, Product.Status.ACTIVE)

    def test_retrieve_product(self):
        product = self.make_product()

        response = self.client.get(self.detail_url(product))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], product.id)


class ProductFeedTests(APITestCase):
    url = reverse("product-feed")

    def setUp(self):
        seller = User.objects.create_user(email="seller@example.com", password="x")
        self.shop = Shop.objects.create(owner=seller, name="Павильон 12")
        self.other_shop = Shop.objects.create(owner=seller, name="Павильон 40")

    def make(self, title="Товар", price="100.00", shop=None, **kwargs):
        return Product.objects.create(shop=shop or self.shop, title=title, price=Decimal(price), **kwargs)

    def fetch_all(self, params=None, page_size=2):
        """Проходит всю ленту по курсорам, как это делает бесконечная прокрутка."""
        params = {**(params or {}), "page_size": page_size}
        ids, cursor, pages = [], None, 0
        while True:
            response = self.client.get(self.url, {**params, **({"cursor": cursor} if cursor else {})})
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            ids += [item["id"] for item in response.data["results"]]
            cursor = response.data["next_cursor"]
            pages += 1
            if cursor is None:
                return ids
            self.assertLess(pages, 100, "лента не заканчивается")

    def ids(self, response):
        return [item["id"] for item in response.data["results"]]

    # --- базовое поведение ---

    def test_is_public_and_returns_cards(self):
        product = self.make(title="iPhone 15", price="79990.00", quantity=0)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["next_cursor"])
        card = response.data["results"][0]
        self.assertEqual(
            {k: v for k, v in card.items() if k != "created_at"},
            {
                "id": product.id,
                "title": "iPhone 15",
                "price": "79990.00",
                "in_stock": False,
                "shop": {"id": self.shop.id, "name": "Павильон 12"},
            },
        )
        self.assertIn("created_at", card)

    def test_archived_products_are_hidden(self):
        active = self.make()
        self.make(status=Product.Status.ARCHIVED)

        self.assertEqual(self.ids(self.client.get(self.url)), [active.id])

    def test_default_sort_is_newest_first(self):
        old, new = self.make(), self.make()

        self.assertEqual(self.ids(self.client.get(self.url)), [new.id, old.id])

    # --- курсорная пагинация ---

    def test_walks_whole_feed_without_duplicates_for_every_sort(self):
        # много одинаковых цен — проверка, что id разруливает «ничьи»
        products = [self.make(price=price) for price in ["300", "100", "200", "100", "100", "300", "200"]]
        by_price = sorted(products, key=lambda p: (p.price, p.id))

        cases = {
            "new": [p.id for p in sorted(products, key=lambda p: (p.created_at, p.id), reverse=True)],
            "price_asc": [p.id for p in by_price],
            "price_desc": [p.id for p in reversed(by_price)],
        }
        for sort, expected in cases.items():
            with self.subTest(sort=sort):
                self.assertEqual(self.fetch_all({"sort": sort}), expected)

    def test_new_products_during_scroll_do_not_cause_duplicates(self):
        initial = [self.make(title=f"P{i}") for i in range(4)]

        first = self.client.get(self.url, {"page_size": 2})
        self.make(title="Добавлен во время прокрутки")
        second = self.client.get(self.url, {"page_size": 2, "cursor": first.data["next_cursor"]})

        seen = self.ids(first) + self.ids(second)
        self.assertEqual(seen, [p.id for p in reversed(initial)])

    def test_pagination_respects_filters(self):
        expected = [self.make(title=f"Чехол {i}").id for i in range(5)]
        for i in range(5):
            self.make(title=f"Зарядка {i}")

        self.assertEqual(self.fetch_all({"q": "чехол"}), list(reversed(expected)))

    def test_cursor_from_another_sort_is_rejected(self):
        for _ in range(3):
            self.make()
        cursor = self.client.get(self.url, {"page_size": 1, "sort": "new"}).data["next_cursor"]

        response = self.client.get(self.url, {"page_size": 1, "sort": "price_asc", "cursor": cursor})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cursor", response.data)

    def test_garbage_cursor_is_400_not_500(self):
        forged = base64.urlsafe_b64encode(json.dumps({"s": "new", "v": "not-a-date", "k": 1}).encode()).decode()
        for cursor in ["garbage", "!!!", forged]:
            with self.subTest(cursor=cursor):
                response = self.client.get(self.url, {"cursor": cursor})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_sort_and_page_size(self):
        for params in [{"sort": "random"}, {"page_size": 0}, {"page_size": 51}, {"page_size": "abc"}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url, params).status_code, status.HTTP_400_BAD_REQUEST)

    # --- фильтры и поиск ---

    def test_search_is_case_insensitive_for_cyrillic_and_handles_yo(self):
        match = self.make(title="Чехол для iPhone", description="Чёрный, силикон")
        self.make(title="Зарядка USB-C")

        for query in ["чехол", "ЧЕХОЛ", "черный", "чёрный", "IPHONE"]:
            with self.subTest(q=query):
                self.assertEqual(self.ids(self.client.get(self.url, {"q": query})), [match.id])

    def test_search_requires_all_words(self):
        both = self.make(title="Чехол iPhone 15")
        self.make(title="Чехол Samsung")

        self.assertEqual(self.ids(self.client.get(self.url, {"q": "iphone чехол"})), [both.id])

    def test_search_text_is_updated_on_save(self):
        product = self.make(title="Старое")
        product.title = "Новое название"
        product.save(update_fields=["title"])

        self.assertEqual(self.ids(self.client.get(self.url, {"q": "новое"})), [product.id])
        self.assertEqual(self.ids(self.client.get(self.url, {"q": "старое"})), [])

    def test_filter_by_shop(self):
        own = self.make(shop=self.shop)
        self.make(shop=self.other_shop)

        self.assertEqual(self.ids(self.client.get(self.url, {"shop": self.shop.id})), [own.id])

    def test_filter_by_price_range(self):
        self.make(price="99.99")
        inside = [self.make(price="100.00"), self.make(price="500.00")]
        self.make(price="500.01")

        response = self.client.get(self.url, {"price_min": "100", "price_max": "500", "sort": "price_asc"})

        self.assertEqual(self.ids(response), [p.id for p in inside])

    def test_filter_in_stock(self):
        available = self.make(quantity=3)
        self.make(quantity=0)

        self.assertEqual(self.ids(self.client.get(self.url, {"in_stock": "true"})), [available.id])

    def test_invalid_filter_values_are_400(self):
        for params in [{"price_min": "abc"}, {"price_min": "500", "price_max": "100"}, {"shop": "x"}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url, params).status_code, status.HTTP_400_BAD_REQUEST)

    def test_single_query_regardless_of_page_size(self):
        for i in range(30):
            self.make(title=f"P{i}", shop=self.shop if i % 2 else self.other_shop)

        with self.assertNumQueries(1):
            self.client.get(self.url, {"page_size": 50, "q": "p"})


class ProductPublicDetailTests(APITestCase):
    def setUp(self):
        seller = User.objects.create_user(email="seller@example.com", password="x")
        self.shop = Shop.objects.create(owner=seller, name="Павильон 12")

    def test_returns_product(self):
        product = Product.objects.create(
            shop=self.shop, title="iPhone 15", description="128 ГБ", price=Decimal("10"), quantity=2
        )

        response = self.client.get(reverse("product-detail", args=[product.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "128 ГБ")
        self.assertEqual(response.data["quantity"], 2)
        self.assertNotIn("search_text", response.data)

    def test_archived_product_is_404(self):
        product = Product.objects.create(
            shop=self.shop, title="X", price=Decimal("10"), status=Product.Status.ARCHIVED
        )

        response = self.client.get(reverse("product-detail", args=[product.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SellerProductFiltersTests(APITestCase):
    """Список товаров в кабинете продавца использует тот же ProductFilter, что и лента."""

    def test_seller_list_supports_feed_filters(self):
        seller = User.objects.create_user(email="seller@example.com", password="x")
        shop = Shop.objects.create(owner=seller, name="Павильон 12")
        match = Product.objects.create(shop=shop, title="Чехол", price=Decimal("150"), quantity=0)
        Product.objects.create(shop=shop, title="Чехол дорогой", price=Decimal("5000"), quantity=0)
        Product.objects.create(shop=shop, title="Зарядка", price=Decimal("150"), quantity=0)
        self.client.force_login(seller)

        response = self.client.get(
            reverse("seller-product-list", args=[shop.id]),
            {"q": "ЧЕХОЛ", "price_max": "1000", "in_stock": "false"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([p["id"] for p in response.data["results"]], [match.id])
        self.assertIn("count", response.data)
