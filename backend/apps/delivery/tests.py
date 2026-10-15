import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.exceptions import BusinessError
from apps.users.models import User

from .models import DeliveryMethod, DeliveryTimeWindow
from .services import get_slots, validate_slot

MSK = ZoneInfo("Europe/Moscow")


def msk(*args):
    return datetime.datetime(*args, tzinfo=MSK)


class SeedTests(TestCase):
    """Стартовый справочник из миграции delivery/0002."""

    def test_pickup_and_market_courier(self):
        pickup = DeliveryMethod.objects.get(code="pickup")
        courier = DeliveryMethod.objects.get(code="market_courier")

        self.assertEqual((pickup.kind, pickup.provider, pickup.price), ("pickup", "shop", Decimal("0.00")))
        self.assertIsNone(pickup.eta_min_days)
        self.assertFalse(pickup.has_slots)
        self.assertFalse(pickup.requires_address)

        self.assertEqual((courier.kind, courier.provider, courier.price), ("courier", "market", Decimal("50.00")))
        self.assertTrue(courier.requires_address)
        self.assertTrue(courier.has_slots)
        self.assertEqual(
            [str(w) for w in courier.time_windows.all()],
            ["10:00–14:00", "14:00–18:00", "18:00–22:00"],
        )

    def test_eta_range_constraint(self):
        with self.assertRaises(IntegrityError):
            DeliveryMethod.objects.create(
                code="bad", name="Bad", kind="courier", provider="market", eta_min_days=3, eta_max_days=1
            )


class DeliveryMethodApiTests(APITestCase):
    url = reverse("delivery-method-list")

    def test_public_list_of_active_methods(self):
        DeliveryMethod.objects.create(code="off", name="Выключен", kind="courier", provider="shop", is_active=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([m["code"] for m in response.data], ["pickup", "market_courier"])
        pickup, courier = response.data
        self.assertEqual(
            pickup,
            {
                "id": pickup["id"],
                "code": "pickup",
                "name": "Самовывоз из павильона",
                "kind": "pickup",
                "provider": "shop",
                "description": "",
                "price": "0.00",
                "eta": None,
                "requires_address": False,
                "has_slots": False,
            },
        )
        self.assertEqual(courier["price"], "50.00")
        self.assertEqual(courier["eta"], {"min_days": 1, "max_days": 2})
        self.assertTrue(courier["has_slots"])

    def test_slots_endpoint(self):
        courier = DeliveryMethod.objects.get(code="market_courier")
        pickup = DeliveryMethod.objects.get(code="pickup")

        response = self.client.get(reverse("delivery-method-slots", args=[courier.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 7 * 3)  # срок от 1 дня — сегодняшних интервалов нет
        first = response.data[0]
        self.assertEqual(set(first), {"date", "window_id", "start", "end"})
        self.assertEqual(first["date"], str(timezone.localdate() + datetime.timedelta(days=1)))
        self.assertEqual((first["start"], first["end"]), ("10:00", "14:00"))

        self.assertEqual(self.client.get(reverse("delivery-method-slots", args=[pickup.id])).data, [])

    def test_inactive_or_unknown_method_slots_are_404(self):
        off = DeliveryMethod.objects.create(code="off", name="X", kind="courier", provider="shop", is_active=False)

        for method_id in [off.id, 999]:
            with self.subTest(method_id=method_id):
                response = self.client.get(reverse("delivery-method-slots", args=[method_id]))
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_pages_render(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))
        courier = DeliveryMethod.objects.get(code="market_courier")

        for url in [
            reverse("admin:delivery_deliverymethod_changelist"),
            reverse("admin:delivery_deliverymethod_change", args=[courier.id]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)


class SlotsServiceTests(TestCase):
    def setUp(self):
        self.method = DeliveryMethod.objects.create(
            code="same_day",
            name="Сегодня",
            kind="courier",
            provider="market",
            eta_min_days=0,
            eta_max_days=1,
            slot_days_ahead=2,
        )
        self.morning = DeliveryTimeWindow.objects.create(
            method=self.method, start_time=datetime.time(10), end_time=datetime.time(14)
        )
        self.day = DeliveryTimeWindow.objects.create(
            method=self.method, start_time=datetime.time(14), end_time=datetime.time(18)
        )
        self.evening = DeliveryTimeWindow.objects.create(
            method=self.method, start_time=datetime.time(18), end_time=datetime.time(22)
        )
        self.now = msk(2026, 10, 15, 15, 0)

    def slots(self, now=None):
        return [(s.date, s.window_id) for s in get_slots(self.method, now=now or self.now)]

    def test_started_windows_today_are_skipped(self):
        today, tomorrow = datetime.date(2026, 10, 15), datetime.date(2026, 10, 16)

        self.assertEqual(
            self.slots(),
            [
                (today, self.evening.id),
                (tomorrow, self.morning.id),
                (tomorrow, self.day.id),
                (tomorrow, self.evening.id),
            ],
        )

    def test_now_is_interpreted_in_project_timezone(self):
        # 23:30 UTC 14-го = 02:30 МСК 15-го → сегодня (по Москве) доступны все интервалы
        now_utc = datetime.datetime(2026, 10, 14, 23, 30, tzinfo=datetime.timezone.utc)

        self.assertEqual(self.slots(now_utc)[0], (datetime.date(2026, 10, 15), self.morning.id))

    def test_inactive_windows_are_not_offered(self):
        self.evening.is_active = False
        self.evening.save()

        self.assertNotIn(self.evening.id, {window_id for _, window_id in self.slots()})

    def test_validate_slot(self):
        slot = validate_slot(self.method, date=datetime.date(2026, 10, 16), window_id=self.day.id, now=self.now)
        self.assertEqual((slot.start, slot.end), (datetime.time(14), datetime.time(18)))

        cases = [
            ({"date": datetime.date(2026, 10, 15), "window_id": self.morning.id}, "slot_unavailable"),  # уже прошёл
            ({"date": datetime.date(2026, 10, 20), "window_id": self.day.id}, "slot_unavailable"),  # слишком далеко
            ({"date": datetime.date(2026, 10, 16), "window_id": 999}, "slot_unavailable"),
            ({"date": None, "window_id": None}, "slot_required"),
        ]
        for kwargs, code in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(BusinessError) as ctx:
                    validate_slot(self.method, now=self.now, **kwargs)
                self.assertEqual(ctx.exception.code, code)

    def test_method_without_slots(self):
        pickup = DeliveryMethod.objects.get(code="pickup")

        self.assertEqual(get_slots(pickup), [])
        self.assertIsNone(validate_slot(pickup, date=None, window_id=None))
        with self.assertRaises(BusinessError) as ctx:
            validate_slot(pickup, date=datetime.date(2026, 10, 16), window_id=self.day.id)
        self.assertEqual(ctx.exception.code, "slot_not_supported")
