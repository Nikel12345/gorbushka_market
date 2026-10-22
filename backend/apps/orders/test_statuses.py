from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User
from apps.wallet.models import WalletTransaction
from apps.wallet.services import change_balance, get_balance

from .models import Order, OrderStatusChange, Purchase
from .services import OrderLine, create_order
from .test_checkout import CheckoutFixturesMixin


class OrderStatusFixturesMixin(CheckoutFixturesMixin):
    """
    Покупка: iPhone (A) и зарядка (B) курьером маркета — одна отправка, два заказа;
    чехол (A) самовывозом — отдельный заказ.
    """

    payment_method = "on_delivery"

    def setUp(self):
        super().setUp()
        self.staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)
        if self.payment_method == "balance":
            change_balance(user=self.buyer, amount=Decimal("5000"), kind=WalletTransaction.Kind.DEPOSIT)
        self.to_cart(self.phone, self.case, self.charger)
        response = self.checkout(
            self.choose((self.phone, self.courier), (self.case, self.pickup), (self.charger, self.courier)),
            "1500.50",
            slots=[self.courier_slot()],
            address="ул. Барклая, 8",
            payment_method=self.payment_method,
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        self.purchase = Purchase.objects.get(pk=response.data["id"])
        orders = self.purchase.orders.select_related("shipment")
        self.pickup_order = orders.get(shipment__delivery_method=self.pickup)
        self.courier_a = orders.get(shipment__delivery_method=self.courier, shop=self.shop_a)
        self.courier_b = orders.get(shipment__delivery_method=self.courier, shop=self.shop_b)
        self.client.logout()

    def seller_set(self, order, new_status, seller=None):
        self.client.force_login(seller or (self.seller_a if order.shop_id == self.shop_a.id else self.seller_b))
        url = reverse("admin-order-status", args=[order.id])
        return self.client.post(url, {"status": new_status}, format="json")

    def market_set(self, order, new_status, user=None):
        self.client.force_login(user or self.staff)
        return self.client.post(reverse("market-order-status", args=[order.id]), {"status": new_status}, format="json")

    def buyer_set(self, order, new_status):
        self.client.force_login(self.buyer)
        return self.client.post(reverse("me-order-status", args=[order.id]), {"status": new_status}, format="json")

    def walk(self, order, *steps):
        for new_status in steps:
            response = self.seller_set(order, new_status)
            assert response.status_code == status.HTTP_200_OK, response.data


class PickupFlowTests(OrderStatusFixturesMixin, APITestCase):
    def test_seller_walks_pickup_order_to_handed_over(self):
        expected = [
            ("confirmed", "Подтверждён", ["ready", "cancelled"]),
            ("ready", "Готов к выдаче", ["completed", "cancelled"]),
            ("completed", "Выдан", []),
        ]
        for new_status, display, next_statuses in expected:
            with self.subTest(status=new_status):
                response = self.seller_set(self.pickup_order, new_status)

                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                self.assertEqual(response.data["status"], new_status)
                self.assertEqual(response.data["status_display"], display)
                self.assertEqual([s["status"] for s in response.data["available_statuses"]], next_statuses)

        changes = OrderStatusChange.objects.filter(order=self.pickup_order)
        self.assertEqual(
            [(c.from_status, c.to_status, c.actor, c.user) for c in changes],
            [
                ("new", "confirmed", "seller", self.seller_a),
                ("confirmed", "ready", "seller", self.seller_a),
                ("ready", "completed", "seller", self.seller_a),
            ],
        )

    def test_list_shows_buttons_for_seller(self):
        self.client.force_login(self.seller_a)

        response = self.client.get(reverse("admin-order-list"))

        order = next(o for o in response.data["results"] if o["id"] == self.pickup_order.id)
        self.assertEqual(
            order["available_statuses"],
            [{"status": "confirmed", "name": "Подтверждён"}, {"status": "cancelled", "name": "Отменён"}],
        )
        self.assertEqual(order["shipment"]["delivery_method"]["code"], "pickup")

    def test_steps_cannot_be_skipped(self):
        response = self.seller_set(self.pickup_order, "completed")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "invalid_transition")
        self.pickup_order.refresh_from_db()
        self.assertEqual(self.pickup_order.status, "new")
        self.assertFalse(OrderStatusChange.objects.exists())

    def test_market_cannot_touch_pickup_orders(self):
        response = self.market_set(self.pickup_order, "confirmed")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_not_staff_gets_403(self):
        response = self.seller_set(self.pickup_order, "confirmed", seller=self.buyer)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_status_is_validation_error(self):
        response = self.seller_set(self.pickup_order, "lost")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_seller_order_detail(self):
        self.client.force_login(self.seller_a)

        response = self.client.get(reverse("admin-order-detail", args=[self.pickup_order.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.pickup_order.id)


class MarketCourierFlowTests(OrderStatusFixturesMixin, APITestCase):
    def test_seller_hands_over_to_courier_and_market_delivers(self):
        response = self.seller_set(self.courier_a, "confirmed")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.seller_set(self.courier_a, "ready")
        self.assertEqual(response.data["status_display"], "Передан курьеру")
        # дальше — не продавец
        self.assertEqual(response.data["available_statuses"], [])
        self.assertEqual(self.seller_set(self.courier_a, "completed").status_code, status.HTTP_400_BAD_REQUEST)

        response = self.market_set(self.courier_a, "completed")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status_display"], "Доставлен")
        self.assertEqual(OrderStatusChange.objects.filter(order=self.courier_a).last().actor, "market")

    def test_market_cannot_deliver_before_handover(self):
        response = self.market_set(self.courier_a, "completed")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "invalid_transition")

    def test_market_api_is_for_staff_only(self):
        self.client.force_login(self.buyer)

        self.assertEqual(self.client.get(reverse("market-order-list")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.market_set(self.courier_a, "completed", user=self.buyer).status_code, 403)

    def test_market_list_contains_courier_orders_with_address(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("market-order-list"), {"status": "new"})

        self.assertEqual({o["id"] for o in response.data["results"]}, {self.courier_a.id, self.courier_b.id})
        order = response.data["results"][0]
        self.assertEqual(order["shipment"]["address"], "ул. Барклая, 8")
        self.assertIn("shop", order)
        self.assertEqual(order["purchase_id"], self.purchase.id)

    def test_seller_does_not_see_buyer_address(self):
        self.client.force_login(self.seller_a)

        response = self.client.get(reverse("admin-order-detail", args=[self.courier_a.id]))

        self.assertNotIn("address", response.data["shipment"])


class BuyerCancelTests(OrderStatusFixturesMixin, APITestCase):
    def test_buyer_can_cancel_new_order_and_stock_returns(self):
        response = self.buyer_set(self.pickup_order, "cancelled")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "cancelled")
        self.case.refresh_from_db()
        self.assertEqual(self.case.quantity, 10)

    def test_buyer_cannot_cancel_confirmed_order(self):
        self.walk(self.pickup_order, "confirmed")

        response = self.buyer_set(self.pickup_order, "cancelled")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_buyer_cannot_confirm(self):
        self.assertEqual(self.buyer_set(self.pickup_order, "confirmed").status_code, status.HTTP_400_BAD_REQUEST)

    def test_buyer_sees_cancel_button(self):
        self.client.force_login(self.buyer)

        purchase = self.client.get(reverse("me-purchase-detail", args=[self.purchase.id])).data
        order = self.client.get(reverse("me-order-detail", args=[self.pickup_order.id])).data

        self.assertEqual(
            {tuple(s["status"] for s in o["available_statuses"]) for o in purchase["orders"]}, {("cancelled",)}
        )
        self.assertEqual(order["available_statuses"], [{"status": "cancelled", "name": "Отменён"}])

    def test_foreign_order_is_404(self):
        other = User.objects.create_user(email="other@example.com", password="x")
        self.client.force_login(other)

        response = self.client.post(
            reverse("me-order-status", args=[self.pickup_order.id]), {"status": "cancelled"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PaymentOnDeliveryTests(OrderStatusFixturesMixin, APITestCase):
    def test_purchase_is_paid_when_everything_not_cancelled_is_handed_over(self):
        self.walk(self.pickup_order, "confirmed", "ready", "completed")
        self.walk(self.courier_a, "confirmed", "ready")
        self.market_set(self.courier_a, "completed")
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.payment_status, "unpaid")

        self.seller_set(self.courier_b, "cancelled")

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.payment_status, "paid")

    def test_seller_sees_purchase_payment(self):
        self.client.force_login(self.seller_a)
        url = reverse("admin-order-detail", args=[self.pickup_order.id])

        data = self.client.get(url).data

        self.assertEqual(data["purchase_id"], self.purchase.id)
        self.assertEqual(data["payment"]["method"], "on_delivery")
        self.assertEqual(data["payment"]["status"], "unpaid")
        self.assertEqual(data["comment"], "")

    def test_cancel_does_not_touch_balance(self):
        self.seller_set(self.pickup_order, "cancelled")

        self.assertFalse(WalletTransaction.objects.filter(kind="refund").exists())


class BalanceRefundTests(OrderStatusFixturesMixin, APITestCase):
    payment_method = "balance"

    def test_refund_goods_then_delivery_when_whole_shipment_cancelled(self):
        self.assertEqual(get_balance(self.buyer), Decimal("3499.50"))

        self.seller_set(self.courier_a, "cancelled")
        # отправка ещё едет (заказ B) — доставку не возвращаем
        self.assertEqual(get_balance(self.buyer), Decimal("4499.50"))

        self.seller_set(self.courier_b, "cancelled")
        # отменена вся отправка — возвращаем и её доставку
        self.assertEqual(get_balance(self.buyer), Decimal("4849.50"))

        self.seller_set(self.pickup_order, "cancelled")
        self.assertEqual(get_balance(self.buyer), Decimal("5000.00"))
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.payment_status, "refunded")
        self.assertEqual(WalletTransaction.objects.filter(kind="refund").count(), 3)

    def test_completed_order_keeps_payment(self):
        self.walk(self.pickup_order, "confirmed", "ready", "completed")

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.payment_status, "paid")
        self.assertEqual(get_balance(self.buyer), Decimal("3499.50"))


class LegacyOrderTests(CheckoutFixturesMixin, APITestCase):
    def test_order_without_shipment_follows_seller_flow(self):
        order = create_order(buyer=self.buyer, shop=self.shop_a, lines=[OrderLine(self.phone.id, 1)])
        self.client.force_login(self.seller_a)

        response = self.client.post(
            reverse("admin-order-status", args=[order.id]), {"status": "confirmed"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIsNone(response.data["shipment"])
        self.assertEqual(Order.objects.get(pk=order.pk).status, "confirmed")


class AdminStatusChangeTests(OrderStatusFixturesMixin, APITestCase):
    payment_method = "balance"

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(email="admin@example.com", password="x")
        self.client.force_login(self.admin)

    def post(self, order, new_status):
        url = reverse("admin:orders_order_change", args=[order.id])
        data = {
            "shop": order.shop_id,
            "buyer": order.buyer_id,
            "purchase": order.purchase_id,
            "shipment": order.shipment_id,
            "status": new_status,
            "total_amount": order.total_amount,
            "bonus_amount": order.bonus_amount,
            "items-TOTAL_FORMS": "0",
            "items-INITIAL_FORMS": "0",
            "status_changes-TOTAL_FORMS": "0",
            "status_changes-INITIAL_FORMS": "0",
        }
        return self.client.post(url, data)

    def test_admin_cancel_goes_through_service(self):
        response = self.post(self.pickup_order, "cancelled")

        self.assertEqual(response.status_code, 302)
        self.pickup_order.refresh_from_db()
        self.assertEqual(self.pickup_order.status, "cancelled")
        change = OrderStatusChange.objects.get(order=self.pickup_order)
        self.assertEqual((change.actor, change.user), ("admin", self.admin))
        # возврат денег и остатков — как при отмене из кабинета
        self.assertEqual(get_balance(self.buyer), Decimal("3650.00"))
        self.case.refresh_from_db()
        self.assertEqual(self.case.quantity, 10)

    def test_admin_can_jump_over_steps(self):
        self.post(self.courier_a, "completed")

        self.courier_a.refresh_from_db()
        self.assertEqual(self.courier_a.status, "completed")

    def test_final_status_cannot_be_left(self):
        self.post(self.pickup_order, "cancelled")

        response = self.post(self.pickup_order, "new")

        self.assertEqual(response.status_code, 200)
        self.assertIn("финальном статусе", str(response.context["adminform"].form.errors))
        self.pickup_order.refresh_from_db()
        self.assertEqual(self.pickup_order.status, "cancelled")
