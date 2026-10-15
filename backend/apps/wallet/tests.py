from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.exceptions import BusinessError
from apps.users.models import User

from .models import Wallet, WalletTransaction
from .services import change_balance, get_balance


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
        self.assertEqual(wallet.balance, Decimal("379.50"))
        journal_sum = sum(t.amount for t in wallet.transactions.all())
        self.assertEqual(journal_sum, wallet.balance)

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

    def test_zero_balance_without_creating_wallet(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"balance": "0.00"})
        self.assertFalse(Wallet.objects.exists())

    def test_returns_current_balance(self):
        change_balance(user=self.user, amount=Decimal("1500.50"), kind=WalletTransaction.Kind.DEPOSIT)
        self.client.force_login(self.user)

        self.assertEqual(self.client.get(self.url).data, {"balance": "1500.50"})

    def test_admin_pages_render(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="x")
        change_balance(user=self.user, amount=Decimal("10"), kind=WalletTransaction.Kind.DEPOSIT)
        self.client.force_login(admin)

        wallet = Wallet.objects.get(user=self.user)
        for url in [reverse("admin:wallet_wallet_changelist"), reverse("admin:wallet_wallet_change", args=[wallet.id])]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
