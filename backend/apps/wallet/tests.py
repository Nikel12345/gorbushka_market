from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.exceptions import BusinessError
from apps.users.models import User

from .models import Bucket, Wallet, WalletOperation, WalletTransaction
from .services import Entry, change_balance, get_balance, get_wallet, post_operation


class ChangeBalanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="buyer@example.com", password="x")

    def test_deposit_creates_wallet_and_journal_entry(self):
        tx = change_balance(user=self.user, amount=Decimal("500.00"), kind=WalletTransaction.Kind.DEPOSIT)

        self.assertEqual(get_balance(self.user), Decimal("500.00"))
        self.assertEqual(tx.amount, Decimal("500.00"))
        self.assertEqual(tx.balance_after, Decimal("500.00"))

    def test_withdrawal_and_journal_consistency(self):
        change_balance(user=self.user, amount=Decimal("500"), kind=WalletTransaction.Kind.DEPOSIT)
        change_balance(user=self.user, amount=Decimal("-120.50"), kind=WalletTransaction.Kind.PAYMENT)

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.available, Decimal("379.50"))
        journal_sum = sum(t.amount for t in wallet.transactions.all())
        self.assertEqual(journal_sum, wallet.available)

    def test_insufficient_funds_changes_nothing(self):
        change_balance(user=self.user, amount=Decimal("100"), kind=WalletTransaction.Kind.DEPOSIT)

        with self.assertRaises(BusinessError) as ctx:
            change_balance(user=self.user, amount=Decimal("-100.01"), kind=WalletTransaction.Kind.PAYMENT)

        self.assertEqual(ctx.exception.code, "insufficient_funds")
        self.assertEqual(get_balance(self.user), Decimal("100.00"))
        self.assertEqual(WalletTransaction.objects.count(), 1)

    def test_zero_amount_is_rejected(self):
        with self.assertRaises(BusinessError):
            change_balance(user=self.user, amount=Decimal("0"), kind=WalletTransaction.Kind.ADJUSTMENT)


class BalanceApiTests(APITestCase):
    url = reverse("me-balance")

    def setUp(self):
        self.user = User.objects.create_user(email="buyer@example.com", password="x")

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_new_user_has_empty_wallet(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"balance": "0.00", "available": "0.00", "bonus": "0.00", "frozen": "0.00", "spendable": "0.00"},
        )
        # кошелёк создаётся вместе с пользователем
        self.assertTrue(Wallet.objects.filter(user=self.user).exists())

    def test_returns_current_balance(self):
        change_balance(user=self.user, amount=Decimal("1500.50"), kind=WalletTransaction.Kind.DEPOSIT)
        change_balance(user=self.user, amount=Decimal("200"), kind=WalletOperation.Kind.BONUS, bucket=Bucket.BONUS)
        self.client.force_login(self.user)

        self.assertEqual(
            self.client.get(self.url).data,
            # balance — как раньше: реальные деньги; spendable — «для покупок» = доступно + бонусы
            {"balance": "1500.50", "available": "1500.50", "bonus": "200.00", "frozen": "0.00", "spendable": "1700.50"},
        )

    def test_admin_pages_render(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="x")
        change_balance(user=self.user, amount=Decimal("10"), kind=WalletTransaction.Kind.DEPOSIT)
        self.client.force_login(admin)

        wallet = Wallet.objects.get(user=self.user)
        for url in [reverse("admin:wallet_wallet_changelist"), reverse("admin:wallet_wallet_change", args=[wallet.id])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)


class WalletBucketsTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(email="seller@example.com", password="x")
        self.buyer = User.objects.create_user(email="buyer@example.com", password="x")

    def test_operation_moves_money_between_buckets_atomically(self):
        post_operation(kind=WalletOperation.Kind.SALE, entries=[Entry(self.seller, Bucket.FROZEN, Decimal("1000"))])

        operation = post_operation(
            kind=WalletOperation.Kind.SALE_RELEASE,
            entries=[Entry(self.seller, Bucket.FROZEN, Decimal("-1000")), Entry(self.seller, Bucket.AVAILABLE, Decimal("900"))],
            description="Выручка за заказ #1",
        )

        wallet = get_wallet(self.seller)
        self.assertEqual((wallet.available, wallet.bonus, wallet.frozen), (Decimal("900"), Decimal("0"), Decimal("0")))
        self.assertEqual(
            [(e.bucket, e.amount, e.balance_after) for e in operation.entries.order_by("id")],
            [("frozen", Decimal("-1000.00"), Decimal("0.00")), ("available", Decimal("900.00"), Decimal("900.00"))],
        )

    def test_any_failing_entry_rolls_back_whole_operation(self):
        change_balance(user=self.buyer, amount=Decimal("100"), kind=WalletOperation.Kind.DEPOSIT)

        with self.assertRaises(BusinessError) as ctx:
            post_operation(
                kind=WalletOperation.Kind.PAYMENT,
                entries=[Entry(self.buyer, Bucket.AVAILABLE, Decimal("-50")), Entry(self.buyer, Bucket.BONUS, Decimal("-1"))],
            )

        self.assertEqual(ctx.exception.code, "insufficient_bonus")
        self.assertEqual(get_balance(self.buyer), Decimal("100.00"))
        self.assertEqual(WalletOperation.objects.count(), 1)

    def test_several_wallets_in_one_operation(self):
        change_balance(user=self.buyer, amount=Decimal("300"), kind=WalletOperation.Kind.DEPOSIT)

        post_operation(
            kind=WalletOperation.Kind.PAYMENT,
            entries=[Entry(self.buyer, Bucket.AVAILABLE, Decimal("-300")), Entry(self.seller, Bucket.FROZEN, Decimal("300"))],
        )

        self.assertEqual(get_wallet(self.buyer).available, Decimal("0.00"))
        self.assertEqual(get_wallet(self.seller).frozen, Decimal("300.00"))

    def test_debt_only_when_allowed_and_only_in_available(self):
        with self.assertRaises(BusinessError):
            post_operation(kind=WalletOperation.Kind.SALE_RELEASE, entries=[Entry(self.seller, Bucket.AVAILABLE, Decimal("-10"))])

        post_operation(
            kind=WalletOperation.Kind.SALE_RELEASE,
            entries=[Entry(self.seller, Bucket.AVAILABLE, Decimal("-10"))],
            allow_debt=True,
        )

        wallet = get_wallet(self.seller)
        self.assertEqual(wallet.available, Decimal("-10.00"))
        # долг не уменьшает бонусы и не даёт тратить «в минус»
        self.assertEqual(wallet.spendable, Decimal("0.00"))
        with self.assertRaises(BusinessError):
            post_operation(
                kind=WalletOperation.Kind.SALE_CANCEL,
                entries=[Entry(self.seller, Bucket.FROZEN, Decimal("-1"))],
                allow_debt=True,
            )

    def test_zero_entries_are_skipped(self):
        self.assertIsNone(
            post_operation(kind=WalletOperation.Kind.REFUND, entries=[Entry(self.buyer, Bucket.BONUS, Decimal("0"))])
        )
        self.assertFalse(WalletOperation.objects.exists())


class WalletAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email="admin@example.com", password="x")
        self.user = User.objects.create_user(email="buyer@example.com", password="x")
        self.wallet = Wallet.objects.get(user=self.user)
        self.client.force_login(self.admin)
        self.url = reverse("admin:wallet_wallet_change", args=[self.wallet.id])

    def post(self, **values):
        data = {"available": "0", "bonus": "0", "frozen": "0", "comment": "", **values}
        # инлайн журнала — пустой формсет
        data.update({"transactions-TOTAL_FORMS": "0", "transactions-INITIAL_FORMS": "0"})
        return self.client.post(self.url, data)

    def test_every_user_has_wallet_in_admin(self):
        response = self.client.get(reverse("admin:wallet_wallet_changelist"))

        self.assertContains(response, "buyer@example.com")

    def test_editing_balances_posts_adjustment_with_entries(self):
        response = self.post(available="150.50", bonus="300", comment="Подарок за отзыв")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_wallet(self.user).available, Decimal("150.50"))
        self.assertEqual(get_wallet(self.user).bonus, Decimal("300.00"))
        operation = WalletOperation.objects.get()
        self.assertEqual(operation.kind, "adjustment")
        self.assertIn("Подарок за отзыв", operation.description)
        self.assertIn("admin@example.com", operation.description)
        self.assertEqual(
            sorted((e.bucket, e.amount) for e in operation.entries.all()),
            [("available", Decimal("150.50")), ("bonus", Decimal("300.00"))],
        )

    def test_decrease_is_negative_entry_and_journal_matches_balance(self):
        self.post(available="500")
        self.post(available="120")

        wallet = Wallet.objects.get(pk=self.wallet.pk)
        self.assertEqual(wallet.available, Decimal("120.00"))
        self.assertEqual(sum(t.amount for t in wallet.transactions.filter(bucket="available")), wallet.available)

    def test_negative_bonus_is_form_error(self):
        response = self.post(bonus="-1")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(WalletOperation.objects.exists())

    def test_saving_without_changes_creates_no_operation(self):
        self.post()

        self.assertFalse(WalletOperation.objects.exists())
