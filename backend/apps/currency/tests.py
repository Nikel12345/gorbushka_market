import datetime
from decimal import Decimal
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.delivery.models import DeliveryMethod
from apps.orders.services import OrderLine, create_order
from apps.shops.models import Shop
from apps.users.models import User

from . import cbr, services
from .models import ExchangeRate
from .services import usd_rate, usd_to_rub

CBR_XML = """<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="21.10.2026" name="Foreign Currency Market">
<Valute ID="R01235"><NumCode>840</NumCode><CharCode>USD</CharCode><Nominal>1</Nominal>
<Name>Доллар США</Name><Value>82,8879</Value><VunitRate>82,8879</VunitRate></Valute>
<Valute ID="R01820"><NumCode>392</NumCode><CharCode>JPY</CharCode><Nominal>100</Nominal>
<Name>Японских иен</Name><Value>54,1234</Value><VunitRate>0,541234</VunitRate></Valute>
</ValCurs>""".encode("cp1251")

TODAY = datetime.date(2026, 10, 21)


class CbrParseTests(TestCase):
    def test_parses_rate_per_unit(self):
        self.assertEqual(cbr.parse_rate(CBR_XML, "USD"), (TODAY, Decimal("82.8879")))
        self.assertEqual(cbr.parse_rate(CBR_XML, "JPY"), (TODAY, Decimal("0.5412")))

    def test_bad_answer_is_cbr_error(self):
        for body in (b"<html>503</html>", b"not xml", CBR_XML.replace(b"USD", b"XXX")):
            with self.subTest(body=body[:20]), self.assertRaises(cbr.CbrError):
                cbr.parse_rate(body, "USD")


@override_settings(USD_RUB_RATE=None)
class UsdRateTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        ExchangeRate.objects.all().delete()  # убираем засеянный миграцией курс

    def fetch(self, **kwargs):
        return mock.patch.object(cbr, "fetch_rate", **kwargs)

    def test_fetches_saves_and_caches_until_midnight(self):
        late_evening = datetime.datetime(2026, 10, 21, 23, 0, tzinfo=ZoneInfo("Europe/Moscow"))
        with (
            self.fetch(return_value=(TODAY, Decimal("82.8879"))) as fetch,
            mock.patch.object(services.timezone, "localtime", return_value=late_evening),
            mock.patch.object(services.cache, "set") as cache_set,
        ):
            rate = usd_rate()

        self.assertEqual((rate.value, rate.date), (Decimal("82.8879"), TODAY))
        fetch.assert_called_once_with("USD", TODAY)
        self.assertEqual(ExchangeRate.objects.get().rate, Decimal("82.8879"))
        cache_set.assert_called_once_with(services.CACHE_KEY, rate, 3600)

    def test_second_call_uses_cache(self):
        with self.fetch(return_value=(TODAY, Decimal("80"))) as fetch:
            usd_rate()
            usd_rate()
        fetch.assert_called_once()

    def test_cbr_down_falls_back_to_saved_rate(self):
        ExchangeRate.objects.create(date=TODAY - datetime.timedelta(days=1), rate=Decimal("81.5"))
        with (
            self.fetch(side_effect=cbr.CbrError("timeout")),
            mock.patch.object(services.cache, "set") as cache_set,
            self.assertLogs(services.logger, "WARNING"),
        ):
            rate = usd_rate()
        self.assertEqual((rate.value, rate.date), (Decimal("81.5"), TODAY - datetime.timedelta(days=1)))
        # Сохранённый курс — ненадолго: ЦБ спросим снова
        cache_set.assert_called_once_with(services.CACHE_KEY, rate, services.RETRY_SECONDS)

    def test_no_rate_at_all_is_503(self):
        with self.fetch(side_effect=cbr.CbrError("timeout")), self.assertLogs(services.logger, "ERROR"):
            response = self.client.get(reverse("currency-usd"))
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.json()["code"], "rate_unavailable")

    def test_rate_endpoint(self):
        with self.fetch(return_value=(TODAY, Decimal("82.8879"))):
            response = self.client.get(reverse("currency-usd"))
        self.assertEqual(response.json(), {"rate": "82.8879", "date": "2026-10-21"})


class UsdToRubTests(TestCase):
    @override_settings(USD_RUB_RATE=Decimal("82.8879"), PRICE_RUB_STEP=Decimal("1"))
    def test_rounds_to_ruble(self):
        self.assertEqual(usd_to_rub(Decimal("965.04")), Decimal("79990.00"))  # 79989.94
        self.assertEqual(usd_to_rub(Decimal("0.01")), Decimal("1.00"))  # 0.83

    @override_settings(USD_RUB_RATE=Decimal("80"), PRICE_RUB_STEP=Decimal("10"))
    def test_rounds_to_step(self):
        self.assertEqual(usd_to_rub(Decimal("10.06")), Decimal("800.00"))  # 804.8
        self.assertEqual(usd_to_rub(Decimal("10.07")), Decimal("810.00"))  # 805.6


@override_settings(USD_RUB_RATE=Decimal("80"), PRICE_RUB_STEP=Decimal("1"))
class RubPricesTests(APITestCase):
    """Цена в долларах в базе, а витрина, фильтр, админка и заказ — в рублях по курсу."""

    def setUp(self):
        self.staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)
        self.shop = Shop.objects.create(name="Павильон 12", address="2 этаж, B-12")

    def make(self, price_usd):
        return Product.objects.create(shop=self.shop, title="Товар", price_usd=Decimal(price_usd), quantity=5)

    def test_feed_card_price_in_rubles(self):
        product = self.make("12.34")  # 987.2 ₽
        card = self.client.get(reverse("product-detail", args=[product.id])).data
        self.assertEqual(card["price"], "987.00")
        self.assertNotIn("price_usd", card)

    @override_settings(USD_RUB_RATE=Decimal("79.97"))
    def test_price_filter_matches_shown_rubles(self):
        # 998.83 → 999 ₽, 999.63 → 1000 ₽, 1000.42 → 1000 ₽, 1001.22 → 1001 ₽
        self.make("12.49")
        shown_1000 = [self.make("12.50"), self.make("12.51")]
        self.make("12.52")

        response = self.client.get(reverse("product-feed"), {"price_min": "1000", "price_max": "1000"})

        self.assertEqual({item["id"] for item in response.data["results"]}, {p.id for p in shown_1000})
        self.assertEqual({item["price"] for item in response.data["results"]}, {"1000.00"})

    def test_admin_sets_dollars_and_sees_rubles(self):
        self.client.force_login(self.staff)
        pickup = DeliveryMethod.objects.get(code="pickup")
        response = self.client.post(
            reverse("admin-product-list"),
            {"title": "iPhone", "price_usd": "999.99", "delivery_method_ids": [pickup.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual((response.data["price_usd"], response.data["price"]), ("999.99", "79999.00"))

    def test_order_keeps_rubles_of_purchase_time(self):
        product = self.make("10.00")
        order = create_order(buyer=self.staff, shop=self.shop, lines=[OrderLine(product.id, 2)])

        with override_settings(USD_RUB_RATE=Decimal("90")):
            item = order.items.get()
            self.assertEqual((item.price, order.total_amount), (Decimal("800.00"), Decimal("1600.00")))
            product.refresh_from_db()
            self.assertEqual(product.price, Decimal("900.00"))
