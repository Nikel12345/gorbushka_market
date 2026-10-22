from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.users.models import User

from .models import Shop


class ShopAdminApiTests(APITestCase):
    """Магазин в админке магазина: /admin/shop/ — только для сотрудников."""

    url = reverse("admin-shop")

    def setUp(self):
        self.staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)
        self.buyer = User.objects.create_user(email="buyer@example.com", password="x")
        self.shop = Shop.objects.create(name="Старое", description="d", address="1 этаж, A-1")
        self.client.force_login(self.staff)

    def test_requires_staff(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(self.url, {"name": "X"}, format="json").status_code, status.HTTP_403_FORBIDDEN)
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, "Старое")

    def test_is_extended_public_info(self):
        Product.objects.create(shop=self.shop, title="A", price_usd=Decimal("1"))

        admin_data = self.client.get(self.url).data
        public_data = self.client.get(reverse("shop-detail", args=[self.shop.id])).data

        # всё публичное есть и в админке, плюс служебные поля
        self.assertLessEqual(public_data.keys(), admin_data.keys())
        self.assertIn("updated_at", admin_data)
        self.assertEqual(admin_data["id"], self.shop.id)
        self.assertEqual(admin_data["address"], "1 этаж, A-1")
        self.assertEqual(admin_data["products_count"], 1)

    def test_patch(self):
        response = self.client.patch(self.url, {"name": "Новое"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Новое")
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, "Новое")
        self.assertEqual(self.shop.description, "d")

    def test_put_and_post_are_not_allowed(self):
        self.assertEqual(
            self.client.put(self.url, {"name": "X"}, format="json").status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(
            self.client.post(self.url, {"name": "Второй"}, format="json").status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        self.assertEqual(Shop.objects.count(), 1)

    def test_shop_not_created_yet_is_404(self):
        Shop.objects.all().delete()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "shop_not_found")

    def test_patch_address_is_trimmed(self):
        response = self.client.patch(self.url, {"address": "  Горбушкин двор, 2 этаж, B-12  "}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["address"], "Горбушкин двор, 2 этаж, B-12")
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.address, "Горбушкин двор, 2 этаж, B-12")

    def test_address_too_long(self):
        response = self.client.patch(self.url, {"address": "a" * 256}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("address", response.data)


class ShopDjangoAdminTests(APITestCase):
    """Магазин один: в админке Django его можно завести, только пока его нет, и нельзя удалить."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email="admin@example.com", password="x")
        self.client.force_login(self.admin)

    def test_add_only_while_there_is_no_shop(self):
        self.assertEqual(self.client.get(reverse("admin:shops_shop_add")).status_code, status.HTTP_200_OK)

        Shop.objects.create(name="Магазин")

        self.assertEqual(self.client.get(reverse("admin:shops_shop_add")).status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_delete(self):
        shop = Shop.objects.create(name="Магазин")

        response = self.client.get(reverse("admin:shops_shop_delete", args=[shop.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ShopPublicTests(APITestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Павильон 12", description="Смартфоны", address="2 этаж, B-12")

    def test_public_shop_page_for_anonymous(self):
        Product.objects.create(shop=self.shop, title="A", price_usd=Decimal("1"))
        Product.objects.create(shop=self.shop, title="B", price_usd=Decimal("1"))
        Product.objects.create(shop=self.shop, title="C", price_usd=Decimal("1"), status=Product.Status.ARCHIVED)

        response = self.client.get(reverse("shop-detail", args=[self.shop.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Павильон 12")
        self.assertEqual(response.data["description"], "Смартфоны")
        self.assertEqual(response.data["address"], "2 этаж, B-12")
        self.assertEqual(response.data["products_count"], 2)
        self.assertNotIn("updated_at", response.data)

    def test_unknown_shop_is_404(self):
        self.assertEqual(self.client.get(reverse("shop-detail", args=[999])).status_code, status.HTTP_404_NOT_FOUND)

    def test_shop_products_come_from_the_shared_feed(self):
        product = Product.objects.create(shop=self.shop, title="A", price_usd=Decimal("1"))
        other_shop = Shop.objects.create(name="Другой")
        Product.objects.create(shop=other_shop, title="B", price_usd=Decimal("1"))

        response = self.client.get(reverse("product-feed"), {"shop": self.shop.id})

        self.assertEqual([p["id"] for p in response.data["results"]], [product.id])
