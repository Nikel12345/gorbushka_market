from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.cart.models import CartItem
from apps.cart.services import add_item
from apps.catalog.models import Product
from apps.delivery.models import DeliveryMethod
from apps.delivery.services import get_slots
from apps.shops.models import Shop
from apps.users.models import User
from apps.wallet.models import WalletTransaction
from apps.wallet.services import change_balance, get_balance

from .models import Order, OrderItem, Purchase, Shipment


class CheckoutFixturesMixin:
    """
    Магазины A и B с адресами, товары с разными способами доставки.
    Способы засеяны миграцией delivery/0002: pickup (0 ₽, магазин), market_courier (50 ₽, маркет, слоты, адрес).
    """

    def setUp(self):
        self.pickup = DeliveryMethod.objects.get(code="pickup")
        self.courier = DeliveryMethod.objects.get(code="market_courier")

        self.seller_a = User.objects.create_user(email="a@example.com", password="x")
        self.seller_b = User.objects.create_user(email="b@example.com", password="x")
        self.buyer = User.objects.create_user(email="buyer@example.com", password="x")
        self.shop_a = Shop.objects.create(owner=self.seller_a, name="Павильон A", address="1 этаж, A-1")
        self.shop_b = Shop.objects.create(owner=self.seller_b, name="Павильон B", address="2 этаж, B-7")

        self.phone = self.make(self.shop_a, "iPhone 15", "1000.00", [self.pickup, self.courier], quantity=5)
        self.case = self.make(self.shop_a, "Чехол", "150.50", [self.pickup, self.courier])
        self.charger = self.make(self.shop_b, "Зарядка", "300.00", [self.pickup, self.courier])

        self.client.force_login(self.buyer)

    def make(self, shop, title, price, methods, quantity=10):
        product = Product.objects.create(shop=shop, title=title, price=Decimal(price), quantity=quantity)
        product.delivery_methods.set(methods)
        return product

    def to_cart(self, *products, quantity=1):
        for product in products:
            add_item(self.buyer, product_id=product.id, quantity=quantity)

    def courier_slot(self):
        slot = get_slots(self.courier)[0]
        return {"delivery_method_id": self.courier.id, "date": slot.date.isoformat(), "window_id": slot.window_id}

    def choose(self, *pairs):
        return [{"product_id": product.id, "delivery_method_id": method.id} for product, method in pairs]

    def checkout(self, items, expected_total, **extra):
        payload = {"items": items, "payment_method": "on_delivery", "expected_total": expected_total, **extra}
        return self.client.post(reverse("me-checkout"), payload, format="json")


class CheckoutPreviewTests(CheckoutFixturesMixin, APITestCase):
    url = reverse("me-checkout")

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_empty_cart(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertFalse(response.data["can_checkout"])
        self.assertEqual(response.data["items_total"], "0.00")

    def test_items_with_delivery_options(self):
        self.to_cart(self.phone, quantity=2)
        self.to_cart(self.charger)

        response = self.client.get(self.url)

        self.assertTrue(response.data["can_checkout"])
        self.assertEqual(response.data["items_total"], "2300.00")
        phone = response.data["items"][0]
        self.assertEqual(phone["product"]["id"], self.phone.id)
        self.assertEqual(phone["quantity"], 2)
        self.assertEqual(phone["total"], "2000.00")
        self.assertEqual([m["code"] for m in phone["delivery_methods"]], ["pickup", "market_courier"])
        # полные условия способа — как в справочнике /delivery/methods/
        self.assertEqual(phone["delivery_methods"][1]["price"], "50.00")
        self.assertTrue(phone["delivery_methods"][1]["has_slots"])
        self.assertEqual(phone["pickup_address"], "1 этаж, A-1")
        self.assertEqual(response.data["unavailable_items"], [])

    def test_payment_methods_and_balance(self):
        change_balance(user=self.buyer, amount=Decimal("500"), kind=WalletTransaction.Kind.DEPOSIT)

        response = self.client.get(self.url)

        self.assertEqual(
            response.data["payment_methods"],
            [{"code": "balance", "name": "С баланса"}, {"code": "on_delivery", "name": "При получении"}],
        )
        self.assertEqual(response.data["balance"], "500.00")

    def test_unavailable_items_are_listed_separately_with_reason(self):
        archived = self.make(self.shop_a, "Снят", "10", [self.pickup])
        short = self.make(self.shop_a, "Мало", "10", [self.pickup], quantity=3)
        no_address_shop = Shop.objects.create(owner=self.seller_b, name="Без адреса")
        pickup_only = self.make(no_address_shop, "Только самовывоз", "10", [self.pickup])
        self.to_cart(self.phone, archived, pickup_only)
        self.to_cart(short, quantity=3)
        Product.objects.filter(pk=archived.pk).update(status=Product.Status.ARCHIVED)
        Product.objects.filter(pk=short.pk).update(quantity=2)

        response = self.client.get(self.url)

        self.assertEqual([i["product"]["id"] for i in response.data["items"]], [self.phone.id])
        problems = {i["product"]["id"]: i["problem"]["code"] for i in response.data["unavailable_items"]}
        self.assertEqual(
            problems,
            {
                archived.id: "product_unavailable",
                pickup_only.id: "no_delivery",
                short.id: "insufficient_stock",
            },
        )
        self.assertEqual(response.data["items_total"], "1000.00")
        self.assertTrue(response.data["can_checkout"])

    def test_own_shop_product_can_be_bought(self):
        own_shop = Shop.objects.create(owner=self.buyer, name="Мой павильон", address="3 этаж")
        own = self.make(own_shop, "Свой", "10", [self.pickup])
        self.to_cart(own)

        response = self.client.get(self.url)

        self.assertEqual([i["product"]["id"] for i in response.data["items"]], [own.id])
        self.assertTrue(response.data["can_checkout"])

    def test_pickup_is_not_offered_when_shop_has_no_address(self):
        no_address_shop = Shop.objects.create(owner=self.seller_b, name="Без адреса")
        product = self.make(no_address_shop, "Товар", "10", [self.pickup, self.courier])
        self.to_cart(product)

        item = self.client.get(self.url).data["items"][0]

        self.assertEqual([m["code"] for m in item["delivery_methods"]], ["market_courier"])
        self.assertIsNone(item["pickup_address"])

    def test_inactive_method_is_not_offered(self):
        self.to_cart(self.phone)
        DeliveryMethod.objects.filter(pk=self.courier.pk).update(is_active=False)

        item = self.client.get(self.url).data["items"][0]

        self.assertEqual([m["code"] for m in item["delivery_methods"]], ["pickup"])

    def test_query_count_does_not_grow_with_items(self):
        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(self.url)
            return len(ctx.captured_queries)

        self.to_cart(self.phone)
        baseline = count_queries()
        for i in range(5):
            self.to_cart(self.make(self.shop_a, f"Товар {i}", "10", [self.pickup, self.courier]))

        self.assertEqual(count_queries(), baseline)


class CheckoutQuoteTests(CheckoutFixturesMixin, APITestCase):
    url = reverse("me-checkout-quote")

    def quote(self, items):
        return self.client.post(self.url, {"items": items}, format="json")

    def test_market_courier_is_paid_once_for_all_items_and_shops(self):
        self.to_cart(self.phone, self.case, self.charger)

        response = self.quote(self.choose((self.phone, self.courier), (self.case, self.courier), (self.charger, self.courier)))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["shipments"]), 1)
        shipment = response.data["shipments"][0]
        self.assertEqual(shipment["delivery_method"]["code"], "market_courier")
        self.assertIsNone(shipment["shop"])
        self.assertEqual(shipment["price"], "50.00")
        self.assertEqual(shipment["product_ids"], [self.phone.id, self.case.id, self.charger.id])
        self.assertEqual(response.data["items_total"], "1450.50")
        self.assertEqual(response.data["delivery_total"], "50.00")
        self.assertEqual(response.data["total_amount"], "1500.50")

    def test_pickup_is_a_separate_shipment_per_shop(self):
        self.to_cart(self.phone, self.case, self.charger)

        response = self.quote(self.choose((self.phone, self.pickup), (self.case, self.pickup), (self.charger, self.pickup)))

        shipments = response.data["shipments"]
        self.assertEqual(
            [(s["shop"]["id"], s["product_ids"]) for s in shipments],
            [(self.shop_a.id, [self.phone.id, self.case.id]), (self.shop_b.id, [self.charger.id])],
        )
        self.assertEqual(response.data["delivery_total"], "0.00")

    def test_mixed_methods(self):
        self.to_cart(self.phone, self.case)

        response = self.quote(self.choose((self.phone, self.courier), (self.case, self.pickup)))

        self.assertEqual(len(response.data["shipments"]), 2)
        self.assertEqual(response.data["total_amount"], "1200.50")

    def test_method_not_available_for_product(self):
        pickup_only = self.make(self.shop_a, "Только самовывоз", "10", [self.pickup])
        self.to_cart(pickup_only)

        response = self.quote(self.choose((pickup_only, self.courier)))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "delivery_unavailable")

    def test_items_must_match_cart(self):
        self.to_cart(self.phone, self.case)

        missing = self.quote(self.choose((self.phone, self.pickup)))
        extra = self.quote(self.choose((self.phone, self.pickup), (self.case, self.pickup), (self.charger, self.pickup)))

        self.assertEqual(missing.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(missing.data["code"], "cart_changed")
        self.assertEqual(extra.status_code, status.HTTP_409_CONFLICT)

    def test_duplicate_product(self):
        self.to_cart(self.phone)

        response = self.quote(self.choose((self.phone, self.pickup), (self.phone, self.courier)))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "duplicate_product")

    def test_empty_items_rejected(self):
        self.assertEqual(self.quote([]).status_code, status.HTTP_400_BAD_REQUEST)

    def test_nothing_is_saved(self):
        self.to_cart(self.phone)

        self.quote(self.choose((self.phone, self.pickup)))

        self.assertFalse(Purchase.objects.exists())
        self.assertEqual(CartItem.objects.count(), 1)


class PlacePurchaseTests(CheckoutFixturesMixin, APITestCase):
    def assert_nothing_created(self):
        self.assertFalse(Purchase.objects.exists())
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Shipment.objects.exists())

    def test_places_purchase_paid_on_delivery(self):
        self.to_cart(self.phone, quantity=2)
        self.to_cart(self.case, self.charger)
        archived = self.make(self.shop_a, "Снят", "10", [self.pickup])
        self.to_cart(archived)
        archived.status = Product.Status.ARCHIVED
        archived.save()

        response = self.checkout(
            self.choose((self.phone, self.courier), (self.case, self.pickup), (self.charger, self.courier)),
            "2500.50",
            slots=[self.courier_slot()],
            address="  ул. Барклая, 8, кв. 5  ",
            comment="Позвонить заранее",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        purchase = Purchase.objects.get()
        self.assertEqual(purchase.buyer, self.buyer)
        self.assertEqual(purchase.payment_method, "on_delivery")
        self.assertEqual(purchase.payment_status, "unpaid")
        self.assertEqual(purchase.items_total, Decimal("2450.50"))
        self.assertEqual(purchase.delivery_total, Decimal("50.00"))
        self.assertEqual(purchase.total_amount, Decimal("2500.50"))
        self.assertEqual(purchase.comment, "Позвонить заранее")

        # курьер маркета — одна отправка на оба магазина, самовывоз — отдельная
        courier = purchase.shipments.get(delivery_method=self.courier)
        pickup = purchase.shipments.get(delivery_method=self.pickup)

        # заказ = магазин × отправка, сумма — только товары заказа
        orders = {(order.shop_id, order.shipment_id): order for order in purchase.orders.all()}
        self.assertEqual(
            {key: order.total_amount for key, order in orders.items()},
            {
                (self.shop_a.id, courier.id): Decimal("2000.00"),
                (self.shop_a.id, pickup.id): Decimal("150.50"),
                (self.shop_b.id, courier.id): Decimal("300.00"),
            },
        )
        self.assertTrue(all(order.buyer == self.buyer and order.status == "new" for order in orders.values()))
        self.assertEqual(courier.price, Decimal("50.00"))
        self.assertIsNone(courier.shop)
        self.assertEqual(courier.address, "ул. Барклая, 8, кв. 5")
        self.assertIsNotNone(courier.slot_date)
        self.assertEqual(pickup.shop, self.shop_a)
        self.assertEqual(pickup.address, "1 этаж, A-1")
        self.assertIsNone(pickup.slot_date)
        self.assertEqual(
            {item.product_id: item.order.shipment for item in OrderItem.objects.select_related("order__shipment")},
            {self.phone.id: courier, self.case.id: pickup, self.charger.id: courier},
        )

        # остатки списаны, купленное ушло из корзины, недоступное осталось
        self.phone.refresh_from_db()
        self.assertEqual(self.phone.quantity, 3)
        self.assertEqual(list(CartItem.objects.values_list("product_id", flat=True)), [archived.id])

        # ответ — покупка целиком
        self.assertEqual(response.data["id"], purchase.id)
        self.assertEqual(response.data["total_amount"], "2500.50")
        self.assertEqual(response.data["payment_status_display"], "Не оплачена")
        self.assertEqual(len(response.data["orders"]), 3)
        self.assertEqual(len(response.data["shipments"]), 2)

    def test_pay_from_balance(self):
        change_balance(user=self.buyer, amount=Decimal("1200"), kind=WalletTransaction.Kind.DEPOSIT)
        self.to_cart(self.phone)

        response = self.checkout(self.choose((self.phone, self.pickup)), "1000.00", payment_method="balance")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        purchase = Purchase.objects.get()
        self.assertEqual(purchase.payment_status, "paid")
        self.assertEqual(get_balance(self.buyer), Decimal("200.00"))
        payment = WalletTransaction.objects.get(kind="payment")
        self.assertEqual(payment.amount, Decimal("-1000.00"))
        self.assertIn(str(purchase.id), payment.description)

    def test_insufficient_balance_rolls_back_everything(self):
        change_balance(user=self.buyer, amount=Decimal("100"), kind=WalletTransaction.Kind.DEPOSIT)
        self.to_cart(self.phone)

        response = self.checkout(self.choose((self.phone, self.pickup)), "1000.00", payment_method="balance")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "insufficient_funds")
        self.assert_nothing_created()
        self.phone.refresh_from_db()
        self.assertEqual(self.phone.quantity, 5)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(get_balance(self.buyer), Decimal("100.00"))

    def test_total_changed_is_conflict(self):
        self.to_cart(self.phone)
        Product.objects.filter(pk=self.phone.pk).update(price=Decimal("1100.00"))

        response = self.checkout(self.choose((self.phone, self.pickup)), "1000.00")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "total_changed")
        self.assert_nothing_created()

    def test_courier_requires_address(self):
        self.to_cart(self.phone)

        response = self.checkout(self.choose((self.phone, self.courier)), "1050.00", slots=[self.courier_slot()], address=" ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "address_required")
        self.assert_nothing_created()

    def test_courier_requires_slot(self):
        self.to_cart(self.phone)

        response = self.checkout(self.choose((self.phone, self.courier)), "1050.00", address="ул. Барклая, 8")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "slot_required")

    def test_unavailable_slot(self):
        self.to_cart(self.phone)
        slot = {**self.courier_slot(), "date": "2000-01-01"}

        response = self.checkout(self.choose((self.phone, self.courier)), "1050.00", slots=[slot], address="ул. Барклая, 8")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "slot_unavailable")

    def test_pickup_needs_neither_slot_nor_address(self):
        self.to_cart(self.phone)

        response = self.checkout(self.choose((self.phone, self.pickup)), "1000.00")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Shipment.objects.get().address, "1 этаж, A-1")

    def test_repeated_submit_is_conflict(self):
        self.to_cart(self.phone)
        items = self.choose((self.phone, self.pickup))

        self.checkout(items, "1000.00")
        response = self.checkout(items, "1000.00")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "cart_changed")
        self.assertEqual(Purchase.objects.count(), 1)

    def test_invalid_payment_method(self):
        self.to_cart(self.phone)

        response = self.checkout(self.choose((self.phone, self.pickup)), "1000.00", payment_method="card")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_method", response.data)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.checkout([], "0").status_code, status.HTTP_403_FORBIDDEN)


class PurchaseVisibilityTests(CheckoutFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.to_cart(self.phone, self.charger)
        response = self.checkout(
            self.choose((self.phone, self.courier), (self.charger, self.pickup)),
            "1350.00",
            slots=[self.courier_slot()],
            address="ул. Барклая, 8",
        )
        self.purchase = Purchase.objects.get(pk=response.data["id"])

    def test_buyer_purchase_list_and_detail(self):
        listing = self.client.get(reverse("me-purchase-list"))
        detail = self.client.get(reverse("me-purchase-detail", args=[self.purchase.id]))

        self.assertEqual([p["id"] for p in listing.data["results"]], [self.purchase.id])
        self.assertIn("next_cursor", listing.data)
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual([o["shop"]["id"] for o in detail.data["orders"]], [self.shop_a.id, self.shop_b.id])
        courier = next(s for s in detail.data["shipments"] if s["delivery_method"]["code"] == "market_courier")
        self.assertEqual(courier["address"], "ул. Барклая, 8")
        self.assertEqual(courier["price"], "50.00")
        self.assertEqual(set(courier["slot"]), {"date", "start", "end"})
        item = detail.data["orders"][0]["items"][0]
        self.assertEqual(item["shipment"]["id"], courier["id"])

    def test_foreign_purchase_is_404(self):
        self.client.force_login(self.seller_a)

        response = self.client.get(reverse("me-purchase-detail", args=[self.purchase.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_buyer_orders_link_to_purchase(self):
        response = self.client.get(reverse("me-order-list"))

        self.assertEqual({o["purchase_id"] for o in response.data["results"]}, {self.purchase.id})

    def test_seller_sees_only_own_part_with_delivery_but_without_buyer_address(self):
        self.client.force_login(self.seller_a)

        response = self.client.get(reverse("seller-order-list", args=[self.shop_a.id]))

        self.assertEqual(response.data["count"], 1)
        order = response.data["results"][0]
        self.assertEqual(order["total_amount"], "1000.00")
        self.assertEqual([i["product_id"] for i in order["items"]], [self.phone.id])
        shipment = order["items"][0]["shipment"]
        self.assertEqual(shipment["delivery_method"]["code"], "market_courier")
        self.assertIsNotNone(shipment["slot"])
        self.assertNotIn("address", shipment)

    def test_purchase_list_query_count_does_not_grow(self):
        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                self.client.get(reverse("me-purchase-list"))
            return len(ctx.captured_queries)

        baseline = count_queries()
        self.to_cart(self.case)
        self.checkout(self.choose((self.case, self.pickup)), "150.50")

        self.assertEqual(count_queries(), baseline)
