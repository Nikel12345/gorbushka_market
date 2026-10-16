import base64
import io
import json
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.delivery.models import DeliveryMethod
from apps.shops.models import Shop
from apps.users.models import User

from .models import Product, ProductImage


def pickup_id():
    """Способы доставки засеяны миграцией delivery/0002."""
    return DeliveryMethod.objects.get(code="pickup").id


class SellerProductTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="seller@example.com", password="x")
        self.other = User.objects.create_user(email="other@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.user, name="Павильон 12", address="2 этаж, B-12")
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
            {"title": "iPhone 15", "description": "128 ГБ", "price": "79990.00", "quantity": 3,
             "delivery_method_ids": [pickup_id()]},
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
            {"title": "X", "price": "10", "status": "archived", "shop": self.foreign_shop.id,
             "delivery_method_ids": [pickup_id()]},
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
                "image": None,
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


def make_image(name="photo.png", size=(10, 10), fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(200, 30, 30)).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


class SellerProductPatchTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="seller@example.com", password="x")
        self.other = User.objects.create_user(email="other@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.owner, name="Павильон 12")
        self.foreign_shop = Shop.objects.create(owner=self.other, name="Чужой")
        self.product = Product.objects.create(
            shop=self.shop, title="iPhone 15", description="128 ГБ", price=Decimal("79990"), quantity=3
        )
        self.client.force_login(self.owner)

    def url(self, product=None, shop=None):
        return reverse("seller-product-detail", args=[(shop or self.shop).id, (product or self.product).id])

    def test_owner_can_patch_fields(self):
        response = self.client.patch(self.url(), {"price": "74990.00", "quantity": 5}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["price"], "74990.00")
        self.assertEqual(response.data["quantity"], 5)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("74990.00"))
        self.assertEqual(self.product.title, "iPhone 15")
        self.assertEqual(self.product.description, "128 ГБ")

    def test_title_change_is_searchable(self):
        self.client.patch(self.url(), {"title": "Samsung Galaxy"}, format="json")

        feed = self.client.get(reverse("product-feed"), {"q": "galaxy"})
        self.assertEqual([p["id"] for p in feed.data["results"]], [self.product.id])

    def test_other_seller_cannot_patch(self):
        self.client.force_login(self.other)

        responses = [
            # через чужой (для него) магазин
            self.client.patch(self.url(), {"price": "1"}, format="json"),
            # подставив свой магазин в URL
            self.client.patch(self.url(shop=self.foreign_shop), {"price": "1"}, format="json"),
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal("79990"))

    def test_anonymous_cannot_patch(self):
        self.client.logout()

        response = self.client.patch(self.url(), {"price": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_change_shop_or_status(self):
        response = self.client.patch(
            self.url(), {"shop": self.foreign_shop.id, "status": "archived"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.shop, self.shop)
        self.assertEqual(self.product.status, Product.Status.ACTIVE)

    def test_validation(self):
        response = self.client.patch(self.url(), {"price": "0", "quantity": -1, "title": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"price", "quantity", "title"})

    def test_archived_product_cannot_be_patched(self):
        self.product.status = Product.Status.ARCHIVED
        self.product.save()

        response = self.client.patch(self.url(), {"price": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_is_not_allowed(self):
        response = self.client.put(self.url(), {"title": "X", "price": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_order_history_keeps_old_price(self):
        from apps.orders.services import OrderLine, create_order

        order = create_order(buyer=self.other, shop=self.shop, lines=[OrderLine(self.product.id, 1)])

        self.client.patch(self.url(), {"price": "1.00", "title": "Новое"}, format="json")

        item = order.items.get()
        self.assertEqual(item.price, Decimal("79990"))
        self.assertEqual(item.title, "iPhone 15")


class ProductImageTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="seller@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.owner, name="Павильон 12", address="2 этаж, B-12")
        self.product = Product.objects.create(shop=self.shop, title="iPhone 15", price=Decimal("10"))
        self.client.force_login(self.owner)
        self.detail_url = reverse("seller-product-detail", args=[self.shop.id, self.product.id])

    def upload(self, image=None):
        return self.client.patch(self.detail_url, {"image": image or make_image()}, format="multipart")

    def test_without_image_everywhere_returns_null(self):
        urls = [
            self.detail_url,
            reverse("product-detail", args=[self.product.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertIsNone(self.client.get(url).data["image"])
        self.assertIsNone(self.client.get(reverse("product-feed")).data["results"][0]["image"])

    def test_upload_image_via_patch(self):
        response = self.upload()

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.product.refresh_from_db()
        self.assertTrue(self.product.image.name.startswith("products/"))
        self.assertTrue(self.product.image.name.endswith(".png"))
        self.assertNotIn("photo", self.product.image.name)  # исходное имя не сохраняется
        self.assertEqual(response.data["image"], f"/media/{self.product.image.name}")

        card = self.client.get(reverse("product-feed")).data["results"][0]
        self.assertEqual(card["image"], response.data["image"])

    def test_create_product_with_image(self):
        response = self.client.post(
            reverse("seller-product-list", args=[self.shop.id]),
            {"title": "С фото", "price": "100", "image": make_image(), "delivery_method_ids": [pickup_id()]},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["image"].startswith("/media/products/"))

    def test_replacing_image_deletes_old_file_after_commit(self):
        self.upload()
        self.product.refresh_from_db()
        old_name = self.product.image.name
        storage = self.product.image.storage

        with self.captureOnCommitCallbacks(execute=True):
            self.upload(make_image("second.jpg", fmt="JPEG"))

        self.product.refresh_from_db()
        self.assertNotEqual(self.product.image.name, old_name)
        self.assertFalse(storage.exists(old_name))
        self.assertTrue(storage.exists(self.product.image.name))

    def test_remove_image_with_null_json_or_empty_multipart(self):
        for payload, fmt in [({"image": None}, "json"), ({"image": ""}, "multipart")]:
            with self.subTest(fmt=fmt):
                self.upload()
                self.product.refresh_from_db()
                old_name = self.product.image.name
                storage = self.product.image.storage

                with self.captureOnCommitCallbacks(execute=True):
                    response = self.client.patch(self.detail_url, payload, format=fmt)

                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                self.assertIsNone(response.data["image"])
                self.product.refresh_from_db()
                self.assertEqual(self.product.image.name, "")
                self.assertFalse(storage.exists(old_name))

    def test_patch_without_image_keeps_it(self):
        self.upload()
        self.product.refresh_from_db()
        name = self.product.image.name

        self.client.patch(self.detail_url, {"price": "20"}, format="json")

        self.product.refresh_from_db()
        self.assertEqual(self.product.image.name, name)

    def test_not_an_image_is_rejected(self):
        fake = SimpleUploadedFile("virus.png", b"definitely not an image", content_type="image/png")

        response = self.upload(fake)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.data)

    @override_settings(PRODUCT_IMAGE_MAX_BYTES=1024)
    def test_too_large_image_is_rejected(self):
        big = make_image("big.bmp", size=(400, 400), fmt="BMP")  # ~480 КБ без сжатия

        response = self.upload(big)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.image.name, "")

    def test_missing_file_in_storage_does_not_crash(self):
        # В БД путь есть, а файла нет (удалили руками, не доехал до S3 и т.п.)
        Product.objects.filter(pk=self.product.pk).update(image="products/lost.png")

        for url in [reverse("product-feed"), reverse("product-detail", args=[self.product.id]), self.detail_url]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)


class ShopPageCursorTests(APITestCase):
    """Листалка товаров на странице магазина = общая лента с ?shop=, курсор работает."""

    def test_cursor_walk_within_shop_with_filters_and_sort(self):
        seller = User.objects.create_user(email="seller@example.com", password="x")
        shop = Shop.objects.create(owner=seller, name="Павильон 12")
        other = Shop.objects.create(owner=seller, name="Другой")
        mine = [
            Product.objects.create(shop=shop, title=f"Чехол {i}", price=Decimal(price))
            for i, price in enumerate(["300", "100", "200", "100", "500"])
        ]
        for i in range(5):
            Product.objects.create(shop=other, title=f"Чехол {i}", price=Decimal("100"))
        Product.objects.create(shop=shop, title="Удалённый", price=Decimal("1"), status=Product.Status.ARCHIVED)

        url = reverse("product-feed")
        for sort, expected in {
            "new": [p.id for p in reversed(mine)],
            "price_asc": [p.id for p in sorted(mine, key=lambda p: (p.price, p.id))],
        }.items():
            with self.subTest(sort=sort):
                ids, cursor, pages = [], None, 0
                while True:
                    params = {"shop": shop.id, "q": "чехол", "sort": sort, "page_size": 2}
                    if cursor:
                        params["cursor"] = cursor
                    response = self.client.get(url, params)
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    ids += [p["id"] for p in response.data["results"]]
                    cursor = response.data["next_cursor"]
                    pages += 1
                    if cursor is None:
                        break
                self.assertEqual(ids, expected)
                self.assertEqual(pages, 3)


class ProductDeliveryMethodsTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="seller@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.owner, name="Павильон 12", address="2 этаж, B-12")
        self.pickup = DeliveryMethod.objects.get(code="pickup")
        self.courier = DeliveryMethod.objects.get(code="market_courier")
        self.client.force_login(self.owner)
        self.list_url = reverse("seller-product-list", args=[self.shop.id])

    def create(self, method_ids, fmt="json", **extra):
        payload = {"title": "iPhone 15", "price": "100", **extra}
        if method_ids is not None:
            payload["delivery_method_ids"] = method_ids
        return self.client.post(self.list_url, payload, format=fmt)

    def detail_url(self, product):
        return reverse("seller-product-detail", args=[self.shop.id, product.id])

    def method_codes(self, data):
        return [m["code"] for m in data["delivery_methods"]]

    def test_create_with_methods(self):
        response = self.create([self.pickup.id, self.courier.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.method_codes(response.data), ["pickup", "market_courier"])
        self.assertNotIn("delivery_method_ids", response.data)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(set(product.delivery_methods.all()), {self.pickup, self.courier})
        # полное описание способа, как в справочнике
        self.assertEqual(response.data["delivery_methods"][1]["price"], "50.00")

    def test_methods_are_required_on_create(self):
        for method_ids in [None, []]:
            with self.subTest(method_ids=method_ids):
                response = self.create(method_ids)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("delivery_method_ids", response.data)
        self.assertFalse(Product.objects.exists())

    def test_unknown_or_inactive_method_is_rejected(self):
        off = DeliveryMethod.objects.create(code="off", name="Выключен", kind="courier", provider="shop", is_active=False)

        for method_ids in [[999], [self.pickup.id, off.id], ["abc"]]:
            with self.subTest(method_ids=method_ids):
                response = self.create(method_ids)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("delivery_method_ids", response.data)
        self.assertFalse(Product.objects.exists())

    def test_duplicates_are_ignored(self):
        response = self.create([self.pickup.id, self.pickup.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.method_codes(response.data), ["pickup"])

    def test_multipart_create_with_repeated_field(self):
        response = self.create([self.pickup.id, self.courier.id], fmt="multipart", image=make_image())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.method_codes(response.data), ["pickup", "market_courier"])

    def test_patch_replaces_methods(self):
        product = Product.objects.get(pk=self.create([self.pickup.id]).data["id"])

        response = self.client.patch(self.detail_url(product), {"delivery_method_ids": [self.courier.id]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.method_codes(response.data), ["market_courier"])
        self.assertEqual(list(product.delivery_methods.all()), [self.courier])

    def test_patch_without_methods_keeps_them_and_empty_is_rejected(self):
        product = Product.objects.get(pk=self.create([self.pickup.id, self.courier.id]).data["id"])

        self.client.patch(self.detail_url(product), {"price": "200"}, format="json")
        self.assertEqual(product.delivery_methods.count(), 2)

        response = self.client.patch(self.detail_url(product), {"delivery_method_ids": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(product.delivery_methods.count(), 2)

    def test_public_detail_shows_only_active_methods(self):
        product = Product.objects.get(pk=self.create([self.pickup.id, self.courier.id]).data["id"])
        self.courier.is_active = False
        self.courier.save()

        response = self.client.get(reverse("product-detail", args=[product.id]))

        self.assertEqual(self.method_codes(response.data), ["pickup"])

    def test_feed_filter_by_delivery_method(self):
        both = Product.objects.get(pk=self.create([self.pickup.id, self.courier.id]).data["id"])
        Product.objects.get(pk=self.create([self.pickup.id]).data["id"])

        response = self.client.get(reverse("product-feed"), {"delivery_method": self.courier.id})

        self.assertEqual([p["id"] for p in response.data["results"]], [both.id])

    def test_seller_list_query_count_does_not_grow(self):
        def count_queries():
            from django.db import connection
            from django.test.utils import CaptureQueriesContext

            with CaptureQueriesContext(connection) as ctx:
                self.client.get(self.list_url)
            return len(ctx.captured_queries)

        self.create([self.pickup.id])
        one = count_queries()
        for _ in range(5):
            self.create([self.pickup.id, self.courier.id])

        self.assertEqual(count_queries(), one)


class SellerAllProductsTests(APITestCase):
    url = reverse("seller-all-products")

    def setUp(self):
        self.owner = User.objects.create_user(email="seller@example.com", password="x")
        self.other = User.objects.create_user(email="other@example.com", password="x")
        self.shop_a = Shop.objects.create(owner=self.owner, name="Павильон A", address="1 этаж")
        self.shop_b = Shop.objects.create(owner=self.owner, name="Павильон B", address="2 этаж")
        self.foreign = Shop.objects.create(owner=self.other, name="Чужой")
        self.client.force_login(self.owner)

    def make(self, shop, title="Товар", **kwargs):
        product = Product.objects.create(shop=shop, title=title, price=Decimal("100"), **kwargs)
        product.delivery_methods.set([DeliveryMethod.objects.get(code="pickup")])
        return product

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_all_own_products_grouped_by_shop(self):
        b_old = self.make(self.shop_b, "B старый")
        a_old = self.make(self.shop_a, "A старый")
        b_new = self.make(self.shop_b, "B новый")
        a_new = self.make(self.shop_a, "A новый")
        self.make(self.foreign, "Чужой")
        self.make(self.shop_a, "Удалённый", status=Product.Status.ARCHIVED)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # без пагинации: просто список
        self.assertIsInstance(response.data, list)
        # магазины подряд в порядке /seller/shops/, внутри — новые сверху
        self.assertEqual([p["id"] for p in response.data], [a_new.id, a_old.id, b_new.id, b_old.id])
        self.assertEqual(response.data[0]["shop"], {"id": self.shop_a.id, "name": "Павильон A"})
        self.assertEqual(response.data[2]["shop"], {"id": self.shop_b.id, "name": "Павильон B"})
        # порядок магазинов совпадает со списком магазинов продавца
        shop_order = [s["id"] for s in self.client.get(reverse("seller-shop-list")).data]
        self.assertEqual(list(dict.fromkeys(p["shop"]["id"] for p in response.data)), shop_order)

    def test_user_without_shops_gets_empty_list(self):
        self.make(self.foreign)
        self.client.force_login(User.objects.create_user(email="buyer@example.com", password="x"))

        self.assertEqual(self.client.get(self.url).data, [])

    def test_supports_shared_product_filters(self):
        match = self.make(self.shop_b, "Чехол iPhone")
        self.make(self.shop_a, "Чехол Samsung")
        self.make(self.shop_b, "Зарядка")

        response = self.client.get(self.url, {"q": "чехол", "shop": self.shop_b.id})

        self.assertEqual([p["id"] for p in response.data], [match.id])

    def test_foreign_shop_filter_returns_nothing(self):
        self.make(self.foreign)

        self.assertEqual(self.client.get(self.url, {"shop": self.foreign.id}).data, [])

    def test_query_count_does_not_grow(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(self.url)
            return len(ctx.captured_queries)

        self.make(self.shop_a)
        baseline = count_queries()
        for i in range(6):
            self.make(self.shop_a if i % 2 else self.shop_b)

        self.assertEqual(count_queries(), baseline)

    def test_per_shop_list_also_contains_shop(self):
        self.make(self.shop_a)

        response = self.client.get(reverse("seller-product-list", args=[self.shop_a.id]))

        self.assertEqual(response.data["results"][0]["shop"], {"id": self.shop_a.id, "name": "Павильон A"})


class PickupRequiresShopAddressTests(APITestCase):
    """Самовывоз можно назначить товару, только если у магазина есть адрес."""

    def setUp(self):
        self.owner = User.objects.create_user(email="seller@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.owner, name="Павильон 12")
        self.pickup = DeliveryMethod.objects.get(code="pickup")
        self.courier = DeliveryMethod.objects.get(code="market_courier")
        self.client.force_login(self.owner)
        self.list_url = reverse("seller-product-list", args=[self.shop.id])

    def create(self, method_ids):
        return self.client.post(
            self.list_url,
            {"title": "iPhone 15", "price": "100", "delivery_method_ids": method_ids},
            format="json",
        )

    def make_product(self, methods):
        product = Product.objects.create(shop=self.shop, title="A", price=Decimal("1"))
        product.delivery_methods.set(methods)
        return product

    def test_pickup_without_shop_address_is_rejected(self):
        response = self.create([self.pickup.id])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["delivery_method_ids"][0].code, "shop_address_required")
        self.assertIn("адрес магазина", str(response.data["delivery_method_ids"][0]))
        self.assertFalse(Product.objects.exists())

    def test_pickup_together_with_courier_is_rejected_too(self):
        response = self.create([self.courier.id, self.pickup.id])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("delivery_method_ids", response.data)

    def test_courier_does_not_need_shop_address(self):
        response = self.create([self.courier.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_pickup_allowed_when_shop_has_address(self):
        self.shop.address = "2 этаж, B-12"
        self.shop.save()

        response = self.create([self.pickup.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_patch_to_pickup_without_address_is_rejected(self):
        product = self.make_product([self.courier])

        response = self.client.patch(
            reverse("seller-product-detail", args=[self.shop.id, product.id]),
            {"delivery_method_ids": [self.pickup.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(list(product.delivery_methods.all()), [self.courier])

    def test_patch_other_fields_does_not_recheck_methods(self):
        # старые товары с самовывозом (проставлен миграцией) редактируются как раньше
        product = self.make_product([self.pickup])

        response = self.client.patch(
            reverse("seller-product-detail", args=[self.shop.id, product.id]), {"price": "200"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_rule_follows_method_kind_and_provider_not_code(self):
        # любой самовывоз силами магазина требует адрес; самовывоз маркета — нет
        shop_pickup = DeliveryMethod.objects.create(
            code="pickup_2", name="Самовывоз со склада", kind="pickup", provider="shop"
        )
        market_pickup = DeliveryMethod.objects.create(
            code="market_pickup", name="Пункт выдачи маркета", kind="pickup", provider="market"
        )

        self.assertEqual(self.create([shop_pickup.id]).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.create([market_pickup.id]).status_code, status.HTTP_201_CREATED)


class ShopAddressInUseTests(APITestCase):
    """Адрес нельзя стереть, пока у товаров магазина выбран самовывоз."""

    def setUp(self):
        self.owner = User.objects.create_user(email="seller@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.owner, name="Павильон 12", address="2 этаж, B-12")
        self.url = reverse("seller-shop-detail", args=[self.shop.id])
        self.client.force_login(self.owner)

    def make_product(self, code, **kwargs):
        product = Product.objects.create(shop=self.shop, title="A", price=Decimal("1"), **kwargs)
        product.delivery_methods.set([DeliveryMethod.objects.get(code=code)])
        return product

    def test_cannot_clear_address_while_products_use_pickup(self):
        self.make_product("pickup")

        for empty in ("", "   "):
            with self.subTest(address=empty):
                response = self.client.patch(self.url, {"address": empty}, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["address"][0].code, "shop_address_in_use")
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.address, "2 этаж, B-12")

    def test_can_change_address_to_another(self):
        self.make_product("pickup")

        response = self.client.patch(self.url, {"address": "1 этаж, A-3"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_can_clear_address_without_pickup_products(self):
        self.make_product("market_courier")
        self.make_product("pickup", status=Product.Status.ARCHIVED)

        response = self.client.patch(self.url, {"address": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.address, "")

    def test_other_shop_pickup_does_not_block(self):
        other = Shop.objects.create(owner=self.owner, name="Другой", address="3 этаж")
        product = Product.objects.create(shop=other, title="B", price=Decimal("1"))
        product.delivery_methods.set([DeliveryMethod.objects.get(code="pickup")])

        response = self.client.patch(self.url, {"address": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProductImagesTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="seller@example.com", password="x")
        self.other = User.objects.create_user(email="other@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.owner, name="Павильон 12", address="2 этаж, B-12")
        self.product = Product.objects.create(shop=self.shop, title="iPhone 15", price=Decimal("10"))
        self.client.force_login(self.owner)
        self.images_url = reverse("seller-product-images", args=[self.shop.id, self.product.id])
        self.order_url = reverse("seller-product-images-order", args=[self.shop.id, self.product.id])
        self.detail_url = reverse("seller-product-detail", args=[self.shop.id, self.product.id])

    def image_url(self, image_id):
        return reverse("seller-product-image-detail", args=[self.shop.id, self.product.id, image_id])

    def upload(self, name="photo.png"):
        return self.client.post(self.images_url, {"image": make_image(name)}, format="multipart")

    def upload_three(self):
        return [self.upload(f"{n}.png").data["id"] for n in range(3)]

    def cover(self):
        self.product.refresh_from_db()
        return self.product.image.name

    def names(self):
        return list(self.product.images.values_list("image", flat=True))

    def test_upload_adds_to_end_and_first_is_cover(self):
        first = self.upload()

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertEqual(set(first.data), {"id", "url"})
        self.assertTrue(first.data["url"].startswith("/media/products/"))
        second = self.upload()

        listed = self.client.get(self.images_url).data
        self.assertEqual([i["id"] for i in listed], [first.data["id"], second.data["id"]])
        self.assertEqual(f"/media/{self.cover()}", first.data["url"])

    def test_images_everywhere_cover_in_cards(self):
        ids = self.upload_three()

        seller = self.client.get(self.detail_url).data
        public = self.client.get(reverse("product-detail", args=[self.product.id])).data
        for data in (seller, public):
            self.assertEqual([i["id"] for i in data["images"]], ids)
            self.assertEqual(data["image"], data["images"][0]["url"])
        card = self.client.get(reverse("product-feed")).data["results"][0]
        self.assertEqual(card["image"], seller["image"])
        self.assertNotIn("images", card)

    def test_create_product_with_several_images(self):
        response = self.client.post(
            reverse("seller-product-list", args=[self.shop.id]),
            {
                "title": "С фото",
                "price": "100",
                "delivery_method_ids": [pickup_id()],
                "images": [make_image("a.png"), make_image("b.jpg", fmt="JPEG")],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(len(response.data["images"]), 2)
        self.assertTrue(response.data["images"][1]["url"].endswith(".jpg"))
        self.assertEqual(response.data["image"], response.data["images"][0]["url"])

    def test_patch_images_appends_and_response_is_fresh(self):
        self.upload()

        response = self.client.patch(self.detail_url, {"images": [make_image(), make_image()]}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["images"]), 3)

    def test_delete_cover_makes_next_one_cover_and_removes_file(self):
        first, second, _ = self.upload_three()
        first_name = ProductImage.objects.get(pk=first).image.name
        storage = self.product.image.storage

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.image_url(first))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.cover(), ProductImage.objects.get(pk=second).image.name)
        self.assertFalse(storage.exists(first_name))

    def test_delete_last_image_clears_cover(self):
        image_id = self.upload().data["id"]

        self.client.delete(self.image_url(image_id))

        self.assertEqual(self.cover(), "")
        self.assertIsNone(self.client.get(self.detail_url).data["image"])

    def test_reorder_changes_cover(self):
        a, b, c = self.upload_three()

        response = self.client.put(self.order_url, {"ids": [c, a, b]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual([i["id"] for i in response.data], [c, a, b])
        self.assertEqual(self.cover(), ProductImage.objects.get(pk=c).image.name)
        self.assertEqual([i["id"] for i in self.client.get(self.images_url).data], [c, a, b])

    def test_reorder_must_list_every_image_once(self):
        a, b, c = self.upload_three()
        foreign = Product.objects.create(shop=self.shop, title="Другой", price=Decimal("1"))
        foreign_image = ProductImage.objects.create(product=foreign, image="products/x.png")

        for ids in ([a, b], [a, b, c, c], [a, b, foreign_image.id]):
            with self.subTest(ids=ids):
                response = self.client.put(self.order_url, {"ids": ids}, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["code"], "image_order_mismatch")
        self.assertEqual([i["id"] for i in self.client.get(self.images_url).data], [a, b, c])

    @override_settings(PRODUCT_IMAGES_MAX=2)
    def test_limit(self):
        self.upload()
        self.upload()

        response = self.upload()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "too_many_images")

        response = self.client.patch(self.detail_url, {"images": [make_image()]}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("images", response.data)
        self.assertEqual(self.product.images.count(), 2)

    def test_not_an_image_is_rejected(self):
        fake = SimpleUploadedFile("virus.png", b"definitely not an image", content_type="image/png")

        response = self.client.post(self.images_url, {"image": fake}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", response.data)
        self.assertFalse(self.product.images.exists())

    def test_legacy_image_field_replaces_only_cover(self):
        ids = self.upload_three()
        b_name = ProductImage.objects.get(pk=ids[1]).image.name

        response = self.client.patch(self.detail_url, {"image": make_image("new.jpg", fmt="JPEG")}, format="multipart")

        # то же первое фото с новым файлом, остальные на месте
        self.assertEqual([i["id"] for i in response.data["images"]], ids)
        self.assertTrue(response.data["image"].endswith(".jpg"))

        response = self.client.patch(self.detail_url, {"image": None}, format="json")

        self.assertEqual(len(response.data["images"]), 2)
        self.assertEqual(self.cover(), b_name)

    def test_other_seller_gets_404(self):
        image_id = self.upload().data["id"]
        self.client.force_login(self.other)

        responses = [
            self.client.get(self.images_url),
            self.client.post(self.images_url, {"image": make_image()}, format="multipart"),
            self.client.delete(self.image_url(image_id)),
            self.client.put(self.order_url, {"ids": [image_id]}, format="json"),
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.product.images.count(), 1)

    def test_image_of_other_product_cannot_be_deleted_via_this_url(self):
        foreign = Product.objects.create(shop=self.shop, title="Другой", price=Decimal("1"))
        foreign_image = ProductImage.objects.create(product=foreign, image="products/x.png")

        response = self.client.delete(self.image_url(foreign_image.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(ProductImage.objects.filter(pk=foreign_image.pk).exists())

    def test_migration_copies_current_image_as_cover(self):
        import importlib

        from django.apps import apps as global_apps

        migration = importlib.import_module("apps.catalog.migrations.0005_product_images")
        Product.objects.filter(pk=self.product.pk).update(image="products/old.png")
        Product.objects.create(shop=self.shop, title="Без фото", price=Decimal("1"))

        migration.copy_current_image(global_apps, None)

        self.assertEqual(
            list(ProductImage.objects.values_list("product_id", "image", "position")),
            [(self.product.id, "products/old.png", 0)],
        )

    def test_admin_inline_reorder_updates_cover(self):
        a, b, _ = self.upload_three()
        admin = User.objects.create_superuser(email="admin@example.com", password="x")
        self.client.force_login(admin)
        url = reverse("admin:catalog_product_change", args=[self.product.id])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        data = {
            "shop": self.shop.id,
            "title": self.product.title,
            "description": "",
            "price": "10",
            "quantity": 1,
            "status": "active",
            "images-TOTAL_FORMS": "3",
            "images-INITIAL_FORMS": "3",
        }
        for index, image in enumerate(self.product.images.all()):
            data[f"images-{index}-id"] = image.id
            data[f"images-{index}-product"] = self.product.id
            data[f"images-{index}-position"] = 0 if image.id == b else index + 1
        data["images-0-DELETE"] = "on"  # первое фото (a) удаляем

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(ProductImage.objects.filter(pk=a).exists())
        self.assertEqual(self.cover(), ProductImage.objects.get(pk=b).image.name)
