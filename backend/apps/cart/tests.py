import datetime
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.catalog.models import Product
from apps.shops.models import Shop
from apps.users.models import User

from .models import Cart, CartItem
from .services import MAX_CART_POSITIONS, delete_stale_guest_carts


class CartTestCase(APITestCase):
    cart_url = reverse("me-cart")
    items_url = reverse("me-cart-items")

    def setUp(self):
        seller = User.objects.create_user(email="seller@example.com", password="x")
        self.buyer = User.objects.create_user(email="buyer@example.com", password="x")
        self.shop = Shop.objects.create(name="Павильон 12")
        self.phone = Product.objects.create(shop=self.shop, title="iPhone 15", price_usd=Decimal("1000.00"), quantity=5)
        self.case = Product.objects.create(shop=self.shop, title="Чехол", price_usd=Decimal("150.50"), quantity=10)
        self.client.force_login(self.buyer)

    def item_url(self, product):
        return reverse("me-cart-item", args=[product.id])

    def add(self, product, quantity=None):
        payload = {"product_id": product.id}
        if quantity is not None:
            payload["quantity"] = quantity
        return self.client.post(self.items_url, payload, format="json")

    def set_quantity(self, product, quantity):
        return self.client.patch(self.item_url(product), {"quantity": quantity}, format="json")

    def quantities(self):
        return dict(CartItem.objects.filter(cart__user=self.buyer).values_list("product_id", "quantity"))


class CartReadTests(CartTestCase):
    def test_empty_cart_without_creating_it(self):
        response = self.client.get(self.cart_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"items": [], "items_count": 0, "total_amount": "0.00", "has_unavailable": False},
        )
        self.assertFalse(Cart.objects.exists())

    def test_cart_contains_resolved_product_cards(self):
        self.add(self.phone, 2)
        self.add(self.case)

        response = self.client.get(self.cart_url)

        self.assertEqual(response.data["items_count"], 3)
        self.assertEqual(response.data["total_amount"], "2150.50")
        self.assertFalse(response.data["has_unavailable"])
        first = response.data["items"][0]
        self.assertEqual(first["quantity"], 2)
        self.assertEqual(first["total"], "2000.00")
        self.assertTrue(first["is_available"])
        self.assertEqual(first["available_quantity"], 5)
        # та же карточка, что в ленте
        feed_card = self.client.get(reverse("product-feed"), {"q": "iphone"}).data["results"][0]
        self.assertEqual(first["product"], feed_card)
        self.assertIsNone(first["product"]["image"])

    def test_items_keep_insertion_order(self):
        self.add(self.case)
        self.add(self.phone)
        self.set_quantity(self.case, 3)

        ids = [i["product"]["id"] for i in self.client.get(self.cart_url).data["items"]]

        self.assertEqual(ids, [self.case.id, self.phone.id])

    def test_cart_shows_current_price(self):
        self.add(self.phone)
        self.phone.price_usd = Decimal("900.00")
        self.phone.save()

        self.assertEqual(self.client.get(self.cart_url).data["total_amount"], "900.00")

    def test_carts_are_isolated_between_users(self):
        self.add(self.phone)
        other = APIClient()
        other.force_login(User.objects.create_user(email="other@example.com", password="x"))

        self.assertEqual(other.get(self.cart_url).data["items"], [])
        other.delete(self.item_url(self.phone))
        self.assertEqual(self.quantities(), {self.phone.id: 1})

    def test_constant_query_count(self):
        products = [
            Product.objects.create(shop=self.shop, title=f"P{i}", price_usd=Decimal("1"), quantity=5) for i in range(10)
        ]
        for product in products:
            self.add(product)

        # сессия + пользователь + корзина + позиции с товарами и магазинами
        with self.assertNumQueries(4):
            self.client.get(self.cart_url)


class CartAddTests(CartTestCase):
    def test_add_returns_full_cart(self):
        response = self.add(self.phone)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["items_count"], 1)
        self.assertEqual(response.data["items"][0]["product"]["id"], self.phone.id)

    def test_adding_same_product_increases_quantity(self):
        self.add(self.phone, 2)
        self.add(self.phone)

        self.assertEqual(self.quantities(), {self.phone.id: 3})

    def test_cannot_add_more_than_in_stock(self):
        self.add(self.phone, 4)

        response = self.add(self.phone, 2)  # итого 6 при остатке 5

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "insufficient_stock")
        self.assertIn("5", response.data["detail"])
        self.assertEqual(self.quantities(), {self.phone.id: 4})

    def test_cannot_add_archived_out_of_stock_or_unknown_product(self):
        archived = Product.objects.create(
            shop=self.shop, title="A", price_usd=Decimal("1"), status=Product.Status.ARCHIVED
        )
        sold_out = Product.objects.create(shop=self.shop, title="B", price_usd=Decimal("1"), quantity=0)

        cases = [
            (archived.id, "product_unavailable"),
            (sold_out.id, "insufficient_stock"),
            (999999, "product_unavailable"),
        ]
        for product_id, code in cases:
            with self.subTest(product_id=product_id):
                response = self.client.post(self.items_url, {"product_id": product_id}, format="json")
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["code"], code)
        self.assertEqual(self.quantities(), {})

    def test_invalid_quantity_on_add(self):
        for quantity in [0, -1, 1000, "abc"]:
            with self.subTest(quantity=quantity):
                self.assertEqual(self.add(self.phone, quantity).status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_product_id(self):
        response = self.client.post(self.items_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("product_id", response.data)

    def test_cart_positions_limit(self):
        cart = Cart.objects.create(user=self.buyer)
        CartItem.objects.bulk_create(
            CartItem(
                cart=cart,
                product=Product.objects.create(shop=self.shop, title=f"P{i}", price_usd=Decimal("1")),
                quantity=1,
            )
            for i in range(MAX_CART_POSITIONS)
        )

        response = self.add(self.phone)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "cart_full")


class CartQuantityTests(CartTestCase):
    def setUp(self):
        super().setUp()
        self.add(self.phone, 2)

    def test_increase_and_decrease(self):
        self.assertEqual(self.set_quantity(self.phone, 5).status_code, status.HTTP_200_OK)
        self.assertEqual(self.quantities(), {self.phone.id: 5})

        response = self.set_quantity(self.phone, 1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"][0]["quantity"], 1)

    def test_quantity_zero_removes_item(self):
        response = self.set_quantity(self.phone, 0)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["items_count"], 0)
        self.assertEqual(self.quantities(), {})

    def test_cannot_increase_above_stock(self):
        response = self.set_quantity(self.phone, 6)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "insufficient_stock")
        self.assertEqual(self.quantities(), {self.phone.id: 2})

    def test_negative_or_invalid_quantity(self):
        for quantity in [-1, 1000, "abc", None]:
            with self.subTest(quantity=quantity):
                self.assertEqual(self.set_quantity(self.phone, quantity).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.quantities(), {self.phone.id: 2})

    def test_patch_product_not_in_cart_is_404(self):
        response = self.set_quantity(self.case, 1)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "not_in_cart")

    def test_can_decrease_even_if_product_became_unavailable(self):
        self.set_quantity(self.phone, 4)
        self.phone.quantity = 1
        self.phone.status = Product.Status.ARCHIVED
        self.phone.save()

        self.assertEqual(self.set_quantity(self.phone, 3).status_code, status.HTTP_200_OK)
        self.assertEqual(self.set_quantity(self.phone, 0).status_code, status.HTTP_200_OK)
        self.assertEqual(self.quantities(), {})


class CartRemoveAndClearTests(CartTestCase):
    def test_remove_item(self):
        self.add(self.phone)
        self.add(self.case)

        response = self.client.delete(self.item_url(self.phone))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([i["product"]["id"] for i in response.data["items"]], [self.case.id])

    def test_remove_is_idempotent(self):
        response = self.client.delete(self.item_url(self.phone))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])

    def test_clear_cart(self):
        self.add(self.phone)
        self.add(self.case)

        response = self.client.delete(self.cart_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(self.quantities(), {})


class CartAvailabilityTests(CartTestCase):
    def test_unavailable_items_are_flagged_and_excluded_from_total(self):
        self.add(self.phone, 3)
        self.add(self.case, 1)
        # после добавления: телефон раскупили до 2 шт., чехол сняли с продажи
        self.phone.quantity = 2
        self.phone.save()
        self.case.status = Product.Status.ARCHIVED
        self.case.save()

        data = self.client.get(self.cart_url).data

        self.assertTrue(data["has_unavailable"])
        self.assertEqual(data["total_amount"], "0.00")
        by_id = {i["product"]["id"]: i for i in data["items"]}
        self.assertFalse(by_id[self.phone.id]["is_available"])
        self.assertEqual(by_id[self.phone.id]["available_quantity"], 2)
        self.assertFalse(by_id[self.case.id]["is_available"])
        self.assertEqual(by_id[self.case.id]["available_quantity"], 0)

        # пользователь уменьшает до доступного — позиция снова доступна
        self.set_quantity(self.phone, 2)
        data = self.client.get(self.cart_url).data
        self.assertEqual(data["total_amount"], "2000.00")


class CartCsrfTests(CartTestCase):
    def test_modifications_require_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.buyer)

        responses = [
            client.post(self.items_url, {"product_id": self.phone.id}, format="json"),
            client.patch(self.item_url(self.phone), {"quantity": 1}, format="json"),
            client.delete(self.cart_url),
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.quantities(), {})


class CartAdminTests(CartTestCase):
    def test_admin_pages_render(self):
        self.add(self.phone)
        admin = User.objects.create_superuser(email="admin@example.com", password="x")
        self.client.force_login(admin)

        cart = Cart.objects.get(user=self.buyer)
        for url in [reverse("admin:cart_cart_changelist"), reverse("admin:cart_cart_change", args=[cart.id])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)


class GuestCartTests(CartTestCase):
    """Корзина гостя — по сессии; при входе переходит в корзину аккаунта."""

    def setUp(self):
        super().setUp()
        cache.clear()  # лимит попыток входа
        self.client.logout()

    def lines(self, client=None):
        data = (client or self.client).get(self.cart_url).data
        return [(line["product"]["id"], line["quantity"]) for line in data["items"]]

    def test_guest_cart_lives_in_session(self):
        self.assertEqual(self.add(self.phone, 2).status_code, status.HTTP_201_CREATED)
        self.set_quantity(self.phone, 3)
        self.add(self.case)

        self.assertEqual(self.lines(), [(self.phone.id, 3), (self.case.id, 1)])
        self.assertIsNone(Cart.objects.get().user)
        # у другого гостя — своя корзина
        self.assertEqual(self.lines(APIClient()), [])

    def test_guest_without_cart(self):
        self.assertEqual(self.lines(), [])
        self.assertEqual(self.set_quantity(self.phone, 1).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(self.item_url(self.phone)).status_code, status.HTTP_200_OK)
        self.assertFalse(Cart.objects.exists())

    def test_guest_cart_moves_to_account_on_login(self):
        self.add(self.phone, 2)
        self.add(self.case)
        CartItem.objects.create(cart=Cart.objects.create(user=self.buyer), product=self.phone, quantity=1)

        response = self.client.post(
            reverse("auth-login"), {"email": "buyer@example.com", "password": "x"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # одинаковые товары сложились, корзина гостя удалена
        self.assertEqual(self.quantities(), {self.phone.id: 3, self.case.id: 1})
        self.assertEqual(Cart.objects.get().user, self.buyer)
        self.assertEqual(dict(self.lines()), {self.phone.id: 3, self.case.id: 1})

    def test_guest_cart_moves_to_new_account_on_registration(self):
        self.add(self.case, 2)

        response = self.client.post(
            reverse("auth-register"), {"email": "new@example.com", "password": "Str0ng-pass!"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.lines(), [(self.case.id, 2)])
        self.assertEqual(Cart.objects.get().user.email, "new@example.com")

    def test_after_logout_guest_cart_is_empty(self):
        self.client.force_login(self.buyer)
        self.add(self.phone)
        self.client.post(reverse("auth-logout"))

        self.assertEqual(self.lines(), [])
        self.assertEqual(self.quantities(), {self.phone.id: 1})

    def test_guest_modifications_require_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)

        response = client.post(self.items_url, {"product_id": self.phone.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Cart.objects.exists())

    def test_stale_guest_carts_are_deleted(self):
        self.add(self.phone)
        stale = Cart.objects.get()
        fresh = Cart.objects.create()
        long_ago = timezone.now() - datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE + 60)
        Cart.objects.filter(pk=stale.pk).update(updated_at=long_ago)
        CartItem.objects.filter(cart=stale).update(updated_at=long_ago)
        Cart.objects.create(user=self.buyer)
        Cart.objects.filter(user=self.buyer).update(updated_at=long_ago)

        self.assertEqual(delete_stale_guest_carts(), 1)
        self.assertEqual(set(Cart.objects.values_list("pk", flat=True)), {fresh.pk, Cart.objects.get(user=self.buyer).pk})
