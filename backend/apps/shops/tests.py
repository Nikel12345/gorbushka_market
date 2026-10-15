from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.users.models import User

from .models import Shop


class SellerProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="seller@example.com", password="x", first_name="Пётр")
        self.other = User.objects.create_user(email="other@example.com", password="x")

    def test_requires_authentication(self):
        response = self.client.get(reverse("seller-profile"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_user_data_and_only_own_shops(self):
        shop = Shop.objects.create(owner=self.user, name="Павильон 12")
        Shop.objects.create(owner=self.other, name="Чужой")
        self.client.force_login(self.user)

        response = self.client.get(reverse("seller-profile"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "seller@example.com")
        self.assertEqual(response.data["first_name"], "Пётр")
        self.assertEqual(response.data["shops"], [{"id": shop.id, "name": "Павильон 12"}])


class SellerShopTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="seller@example.com", password="x")
        self.other = User.objects.create_user(email="other@example.com", password="x")
        self.client.force_login(self.user)

    def test_create_shop(self):
        response = self.client.post(
            reverse("seller-shop-list"),
            {"name": "Павильон 12", "description": "Смартфоны"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        shop = Shop.objects.get(pk=response.data["id"])
        self.assertEqual(shop.owner, self.user)
        self.assertEqual(shop.name, "Павильон 12")

    def test_owner_cannot_be_set_from_request(self):
        response = self.client.post(
            reverse("seller-shop-list"),
            {"name": "Павильон", "owner": self.other.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Shop.objects.get(pk=response.data["id"]).owner, self.user)

    def test_create_shop_requires_name(self):
        response = self.client.post(reverse("seller-shop-list"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_list_returns_only_own_shops(self):
        own = Shop.objects.create(owner=self.user, name="Мой")
        Shop.objects.create(owner=self.other, name="Чужой")

        response = self.client.get(reverse("seller-shop-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([s["id"] for s in response.data], [own.id])

    def test_foreign_shop_detail_is_404(self):
        foreign = Shop.objects.create(owner=self.other, name="Чужой")

        response = self.client.get(reverse("seller-shop-detail", args=[foreign.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_seller_detail_is_extended_public_info(self):
        shop = Shop.objects.create(owner=self.user, name="Павильон 12")
        Product.objects.create(shop=shop, title="A", price=Decimal("1"))

        seller_data = self.client.get(reverse("seller-shop-detail", args=[shop.id])).data
        public_data = self.client.get(reverse("shop-detail", args=[shop.id])).data

        # всё публичное есть и у продавца, плюс служебные поля
        self.assertLessEqual(public_data.keys(), seller_data.keys())
        self.assertIn("updated_at", seller_data)
        self.assertEqual(seller_data["products_count"], 1)

    def test_created_shop_has_products_count(self):
        response = self.client.post(reverse("seller-shop-list"), {"name": "Новый"}, format="json")

        self.assertEqual(response.data["products_count"], 0)

    def test_patch_own_shop(self):
        shop = Shop.objects.create(owner=self.user, name="Старое", description="d")

        response = self.client.patch(
            reverse("seller-shop-detail", args=[shop.id]),
            {"name": "Новое", "owner": self.other.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Новое")
        shop.refresh_from_db()
        self.assertEqual(shop.name, "Новое")
        self.assertEqual(shop.description, "d")
        self.assertEqual(shop.owner, self.user)

    def test_patch_foreign_shop_is_404(self):
        foreign = Shop.objects.create(owner=self.other, name="Чужой")

        response = self.client.patch(reverse("seller-shop-detail", args=[foreign.id]), {"name": "X"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        foreign.refresh_from_db()
        self.assertEqual(foreign.name, "Чужой")

    def test_put_is_not_allowed(self):
        shop = Shop.objects.create(owner=self.user, name="Мой")

        response = self.client.put(reverse("seller-shop-detail", args=[shop.id]), {"name": "X"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ShopPublicTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="seller@example.com", password="x")
        self.shop = Shop.objects.create(owner=self.owner, name="Павильон 12", description="Смартфоны")

    def test_public_shop_page_for_anonymous(self):
        Product.objects.create(shop=self.shop, title="A", price=Decimal("1"))
        Product.objects.create(shop=self.shop, title="B", price=Decimal("1"))
        Product.objects.create(shop=self.shop, title="C", price=Decimal("1"), status=Product.Status.ARCHIVED)

        response = self.client.get(reverse("shop-detail", args=[self.shop.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Павильон 12")
        self.assertEqual(response.data["description"], "Смартфоны")
        self.assertEqual(response.data["products_count"], 2)
        self.assertNotIn("owner", response.data)
        self.assertNotIn("updated_at", response.data)

    def test_unknown_shop_is_404(self):
        self.assertEqual(self.client.get(reverse("shop-detail", args=[999])).status_code, status.HTTP_404_NOT_FOUND)

    def test_shop_products_come_from_the_shared_feed(self):
        product = Product.objects.create(shop=self.shop, title="A", price=Decimal("1"))
        other_shop = Shop.objects.create(owner=self.owner, name="Другой")
        Product.objects.create(shop=other_shop, title="B", price=Decimal("1"))

        response = self.client.get(reverse("product-feed"), {"shop": self.shop.id})

        self.assertEqual([p["id"] for p in response.data["results"]], [product.id])
