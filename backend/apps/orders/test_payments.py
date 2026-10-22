from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.wallet.models import Bucket, WalletOperation, WalletTransaction
from apps.wallet.services import change_balance, get_wallet

from . import statuses
from .models import Order, OrderStatusChange, Purchase, Shipment
from .payments import allocate
from .test_checkout import CheckoutFixturesMixin

D = Decimal
Actor = OrderStatusChange.Actor


class PaymentFixturesMixin(CheckoutFixturesMixin):
    """
    Корзина: iPhone 1000 (A, курьер), чехол 150.50 (A, самовывоз), зарядка 300 (B, курьер).
    Итог: 1450.50 товары + 50 доставка = 1500.50.
    """

    def fund(self, available="0", bonus="0"):
        if D(available):
            change_balance(user=self.buyer, amount=D(available), kind=WalletOperation.Kind.DEPOSIT)
        if D(bonus):
            change_balance(user=self.buyer, amount=D(bonus), kind=WalletOperation.Kind.BONUS, bucket=Bucket.BONUS)

    def items(self):
        return self.choose((self.phone, self.courier), (self.case, self.pickup), (self.charger, self.courier))

    def place(self, payment_method="balance", use_bonus=True):
        self.to_cart(self.phone, self.case, self.charger)
        response = self.checkout(
            self.items(),
            "1500.50",
            slots=[self.courier_slot()],
            address="ул. Барклая, 8",
            payment_method=payment_method,
            use_bonus=use_bonus,
        )
        return response

    def placed(self, **kwargs):
        response = self.place(**kwargs)
        assert response.status_code == status.HTTP_201_CREATED, response.data
        self.purchase = Purchase.objects.get(pk=response.data["id"])
        orders = self.purchase.orders.select_related("shipment")
        self.courier_a = orders.get(shop=self.shop_a, shipment__delivery_method=self.courier)
        self.pickup_a = orders.get(shop=self.shop_a, shipment__delivery_method=self.pickup)
        self.courier_b = orders.get(shop=self.shop_b)
        return response

    def set_status(self, order, *steps, actor=Actor.SELLER):
        for step in steps:
            user = self.staff if actor == Actor.MARKET else self.seller_a
            statuses.change_status(order, to=step, actor=actor, user=user)
        order.refresh_from_db()

    def wallet(self, user):
        w = get_wallet(user)
        return w.available, w.bonus


class AllocateTests(TestCase):
    def test_shares_sum_exactly_and_are_proportional(self):
        shares = allocate(D("300.00"), [D("1000.00"), D("150.50"), D("300.00"), D("50.00")])

        # 300 × вес / 1500.50 с округлением вниз; 2 оставшиеся копейки — самой большой доле
        self.assertEqual(shares, [D("199.95"), D("30.08"), D("59.98"), D("9.99")])
        self.assertEqual(sum(shares), D("300.00"))

    def test_zero(self):
        self.assertEqual(allocate(D("0"), [D("10"), D("20")]), [D("0.00"), D("0.00")])


class BonusCheckoutTests(PaymentFixturesMixin, APITestCase):
    def test_preview_shows_bonus_switch_data(self):
        self.fund(available="100", bonus="250")

        response = self.client.get(reverse("me-checkout"))

        self.assertEqual(response.data["balance"], "100.00")
        self.assertEqual(response.data["bonus"], "250.00")
        self.assertEqual(response.data["bonus_max_share"], "0.50")

    def test_quote_with_bonus_is_capped_at_half(self):
        self.fund(bonus="5000")
        self.to_cart(self.phone, self.case, self.charger)

        with_bonus = self.client.post(reverse("me-checkout-quote"), {"items": self.items(), "use_bonus": True}, format="json")
        without = self.client.post(reverse("me-checkout-quote"), {"items": self.items()}, format="json")

        self.assertEqual(with_bonus.data["total_amount"], "1500.50")
        self.assertEqual(with_bonus.data["bonus_amount"], "750.25")
        self.assertEqual(with_bonus.data["amount_to_pay"], "750.25")
        self.assertEqual(without.data["bonus_amount"], "0.00")
        self.assertEqual(without.data["amount_to_pay"], "1500.50")

    def test_pay_from_balance_with_all_bonuses(self):
        self.fund(available="2000", bonus="300")

        response = self.placed(payment_method="balance")

        self.assertEqual(response.data["bonus_amount"], "300.00")
        self.assertEqual(self.purchase.payment_status, "paid")
        self.assertEqual(self.wallet(self.buyer), (D("799.50"), D("0.00")))
        # бонусы разложены по заказам и платной доставке — до копейки
        orders_bonus = sum(o.bonus_amount for o in self.purchase.orders.all())
        delivery_bonus = sum(s.bonus_amount for s in self.purchase.shipments.all())
        self.assertEqual(orders_bonus + delivery_bonus, D("300.00"))
        self.assertEqual(Shipment.objects.get(delivery_method=self.pickup).bonus_amount, D("0.00"))
        # выручка магазина в кошельки не попадает: проводки только у покупателя
        self.assertFalse(WalletTransaction.objects.exclude(wallet__user=self.buyer).exists())

    def test_bonus_switch_off_keeps_bonuses(self):
        self.fund(available="2000", bonus="300")

        self.placed(payment_method="balance", use_bonus=False)

        self.assertEqual(self.wallet(self.buyer), (D("499.50"), D("300.00")))

    def test_not_enough_money_for_the_rest_rolls_back_bonuses(self):
        self.fund(available="100", bonus="300")

        response = self.place(payment_method="balance")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "insufficient_funds")
        self.assertEqual(self.wallet(self.buyer), (D("100.00"), D("300.00")))
        self.assertFalse(Purchase.objects.exists())

    def test_on_delivery_with_bonuses(self):
        self.fund(bonus="300")

        self.placed(payment_method="on_delivery")

        self.assertEqual(self.purchase.payment_status, "unpaid")
        self.assertEqual(self.wallet(self.buyer), (D("0.00"), D("0.00")))
        # при выдаче — сумма минус бонусная доля
        self.assertEqual(self.pickup_a.amount_due, self.pickup_a.total_amount - self.pickup_a.bonus_amount)
        due = sum(o.amount_due for o in self.purchase.orders.all()) + sum(
            s.amount_due for s in self.purchase.shipments.all()
        )
        self.assertEqual(due, D("1200.50"))

    def test_amounts_in_api(self):
        self.fund(bonus="300")
        self.placed(payment_method="on_delivery")

        self.client.force_login(self.seller_a)
        order = self.client.get(reverse("admin-order-detail", args=[self.pickup_a.id])).data

        self.assertEqual(D(order["amount_due"]), self.pickup_a.amount_due)
        self.assertEqual(D(order["bonus_amount"]), self.pickup_a.bonus_amount)
        self.assertNotIn("commission_amount", order)
        self.assertNotIn("seller_amount", order)


class HandoverTests(PaymentFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        from apps.users.models import User

        self.staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)

    def assert_handover_does_not_touch_wallets(self, payment_method):
        self.fund(available="2000", bonus="300")
        self.placed(payment_method=payment_method)
        operations = WalletOperation.objects.count()
        buyer_wallet = self.wallet(self.buyer)

        self.set_status(self.pickup_a, "confirmed", "ready", "completed")
        self.set_status(self.courier_b, "confirmed", "ready")
        self.set_status(self.courier_b, "completed", actor=Actor.MARKET)

        self.assertEqual(WalletOperation.objects.count(), operations)
        self.assertEqual(self.wallet(self.buyer), buyer_wallet)

    def test_balance_payment(self):
        self.assert_handover_does_not_touch_wallets("balance")

    def test_payment_on_delivery(self):
        self.assert_handover_does_not_touch_wallets("on_delivery")


class RefundTests(PaymentFixturesMixin, APITestCase):
    def test_cancel_everything_returns_money_and_bonuses_exactly(self):
        self.fund(available="2000", bonus="300")
        self.placed(payment_method="balance")

        self.set_status(self.courier_a, "cancelled")
        available, bonus = self.wallet(self.buyer)
        # отправка ещё едет (заказ B) — доставку не возвращаем
        self.assertEqual(available - D("799.50"), D("1000.00") - self.courier_a.bonus_amount)
        self.assertEqual(bonus, self.courier_a.bonus_amount)

        self.set_status(self.courier_b, "cancelled")
        self.set_status(self.pickup_a, "cancelled")

        self.assertEqual(self.wallet(self.buyer), (D("2000.00"), D("300.00")))
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.payment_status, "refunded")

    def test_on_delivery_cancel_returns_only_bonuses(self):
        self.fund(bonus="300")
        self.placed(payment_method="on_delivery")

        for order in (self.courier_a, self.courier_b, self.pickup_a):
            self.set_status(order, "cancelled")

        self.assertEqual(self.wallet(self.buyer), (D("0.00"), D("300.00")))
        self.assertEqual(Order.objects.filter(status="cancelled").count(), 3)
