import io
from datetime import timedelta
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.validators import validate_site_link
from apps.users.models import User

from .models import Promo


def make_image(name="promo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (40, 10), color=(30, 30, 200)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class FeedPromoApiTests(APITestCase):
    url = reverse("promo-feed")

    def make(self, title, **kwargs):
        return Promo.objects.create(title=title, image=make_image(), **kwargs)

    def get_with_offset(self, offset):
        # Подменяем случайное смещение среди показываемых полос
        with mock.patch("apps.promo.views.random.randrange", return_value=offset) as randrange:
            response = self.client.get(self.url)
        return response, randrange

    def test_random_record_among_live_only(self):
        now = timezone.now()
        second = self.make("Вторая", position=2, url="/?q=чехол")
        first = self.make("Первая", position=1, url="https://example.com/sale", image_mobile=make_image())
        self.make("Выключена", is_active=False)
        self.make("Ещё не началась", starts_at=now + timedelta(hours=1))
        self.make("Закончилась", ends_at=now - timedelta(minutes=1))
        current = self.make("В периоде", position=3, starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1))

        ids = []
        for offset in range(3):
            response, randrange = self.get_with_offset(offset)
            randrange.assert_called_once_with(3)  # выбор только из трёх показываемых
            ids.append(response.data["id"])

        self.assertEqual(ids, [first.id, second.id, current.id])
        record = self.get_with_offset(0)[0].data
        self.assertEqual(set(record), {"id", "title", "image", "image_mobile", "url"})
        self.assertTrue(record["image"].startswith("/media/promo/"))
        self.assertTrue(record["image_mobile"].startswith("/media/promo/"))
        self.assertEqual(self.get_with_offset(1)[0].data["url"], "/?q=чехол")
        self.assertIsNone(self.get_with_offset(1)[0].data["image_mobile"])

    def test_promo_without_link(self):
        self.make("Без ссылки")

        self.assertEqual(self.client.get(self.url).data["url"], "")

    def test_no_promos_is_204(self):
        self.make("Выключена", is_active=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PromoModelTests(TestCase):
    def test_site_link_validation(self):
        for good in ["/", "/?q=чехол", "/catalog/products/7/?from=promo", "https://example.com", "http://example.com/a"]:
            with self.subTest(good=good):
                validate_site_link(good)
        for bad in ["javascript:alert(1)", "data:text/html,x", "//evil.com", "/\\evil.com", "shops/5", "/a b"]:
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                validate_site_link(bad)

    def test_period_must_end_after_start(self):
        now = timezone.now()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Promo.objects.create(title="x", image="promo/x.png", starts_at=now, ends_at=now)

    def test_deleting_removes_files_after_commit(self):
        promo = Promo.objects.create(title="x", image=make_image(), image_mobile=make_image())
        names = [promo.image.name, promo.image_mobile.name]
        storage = promo.image.storage

        with self.captureOnCommitCallbacks(execute=True):
            promo.delete()

        self.assertFalse(any(storage.exists(name) for name in names))


class PromoAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))

    def test_pages_render_and_replacing_image_deletes_old_file(self):
        promo = Promo.objects.create(title="x", image=make_image())
        old_name, storage = promo.image.name, promo.image.storage
        url = reverse("admin:promo_promo_change", args=[promo.id])
        for page in [reverse("admin:promo_promo_changelist"), reverse("admin:promo_promo_add"), url]:
            with self.subTest(page=page):
                self.assertEqual(self.client.get(page).status_code, 200)

        data = {"placement": "feed", "title": "x", "image": make_image("new.png"), "url": "/", "position": 0}
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        promo.refresh_from_db()
        self.assertNotEqual(promo.image.name, old_name)
        self.assertFalse(storage.exists(old_name))

    def test_bad_link_is_form_error(self):
        response = self.client.post(
            reverse("admin:promo_promo_add"),
            {"placement": "feed", "title": "x", "image": make_image(), "url": "javascript:alert(1)", "position": 0},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Promo.objects.exists())
