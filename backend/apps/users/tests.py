from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import User

PASSWORD = "Sup3r-secret-pass"


class AuthTestCase(APITestCase):
    def setUp(self):
        # Счётчики throttling живут в кеше — сбрасываем между тестами
        cache.clear()

    def register(self, client=None, **overrides):
        payload = {"email": "buyer@example.com", "password": PASSWORD, **overrides}
        return (client or self.client).post(reverse("auth-register"), payload, format="json")

    def login(self, client=None, **overrides):
        payload = {"email": "buyer@example.com", "password": PASSWORD, **overrides}
        return (client or self.client).post(reverse("auth-login"), payload, format="json")


class RegisterTests(AuthTestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.register(first_name="Иван")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "buyer@example.com")
        self.assertEqual(response.data["first_name"], "Иван")
        self.assertNotIn("password", response.data)
        self.assertTrue(User.objects.get(email="buyer@example.com").check_password(PASSWORD))

        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)

    def test_email_is_normalized_to_lowercase(self):
        response = self.register(email="  Buyer@Example.COM ")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "buyer@example.com")

    def test_duplicate_email_is_rejected_case_insensitive(self):
        User.objects.create_user(email="buyer@example.com", password=PASSWORD)

        response = self.register(email="BUYER@example.com")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_weak_password_is_rejected(self):
        response = self.register(password="123")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.exists())


class LoginLogoutTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email="buyer@example.com", password=PASSWORD)

    def test_login_success(self):
        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)

    def test_login_is_case_insensitive_by_email(self):
        response = self.login(email="Buyer@Example.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_wrong_password(self):
        response = self.login(password="wrong-password")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_login_inactive_user_fails_with_same_error(self):
        self.user.is_active = False
        self.user.save()

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_logout(self):
        self.login()

        response = self.client.post(reverse("auth-logout"))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_403_FORBIDDEN)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me_tells_whether_admin_is_available(self):
        customer = User.objects.create_user(email="customer@example.com", password="x")
        staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)

        for user, expected in ((customer, False), (staff, True)):
            self.client.force_login(user)
            self.assertIs(self.client.get(reverse("auth-me")).data["is_staff"], expected)

    def test_login_is_throttled(self):
        for _ in range(10):
            self.login(password="wrong-password")

        response = self.login()

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class CsrfTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user(email="buyer@example.com", password=PASSWORD)
        self.csrf_client = APIClient(enforce_csrf_checks=True)

    def test_login_without_csrf_token_is_rejected(self):
        response = self.login(client=self.csrf_client)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_with_csrf_token_succeeds(self):
        self.csrf_client.get(reverse("auth-csrf"))
        token = self.csrf_client.cookies["csrftoken"].value

        response = self.csrf_client.post(
            reverse("auth-login"),
            {"email": "buyer@example.com", "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_logout_without_csrf_token_is_rejected_for_logged_in_user(self):
        self.csrf_client.get(reverse("auth-csrf"))
        token = self.csrf_client.cookies["csrftoken"].value
        self.csrf_client.post(
            reverse("auth-login"),
            {"email": "buyer@example.com", "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

        response = self.csrf_client.post(reverse("auth-logout"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserManagerTests(AuthTestCase):
    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="Admin@Example.com", password=PASSWORD)

        self.assertEqual(admin.email, "admin@example.com")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)


class AdminTests(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(email="admin@example.com", password=PASSWORD)
        self.client.force_login(self.admin)

    def test_admin_pages_render(self):
        for url in [
            reverse("admin:users_user_changelist"),
            reverse("admin:users_user_add"),
            reverse("admin:users_user_change", args=[self.admin.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_admin_can_create_user(self):
        response = self.client.post(
            reverse("admin:users_user_add"),
            {"email": "Seller@Example.com", "password1": PASSWORD, "password2": PASSWORD},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(User.objects.filter(email="seller@example.com").exists())


class ProfileTests(AuthTestCase):
    url = reverse("me-profile")

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email="buyer@example.com", password=PASSWORD, first_name="Анна")

    def test_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN)

    def test_get_profile(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "buyer@example.com")
        self.assertEqual(response.data["first_name"], "Анна")

    def test_patch_updates_names_and_returns_full_profile(self):
        self.client.force_login(self.user)

        response = self.client.patch(self.url, {"last_name": "Иванова"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_name"], "Иванова")
        self.assertEqual(response.data["first_name"], "Анна")
        self.assertEqual(response.data["email"], "buyer@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, "Иванова")

    def test_email_and_privileges_cannot_be_changed(self):
        self.client.force_login(self.user)

        self.client.patch(
            self.url,
            {"email": "hacker@example.com", "is_staff": True, "is_superuser": True},
            format="json",
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "buyer@example.com")
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_put_is_not_allowed(self):
        self.client.force_login(self.user)

        response = self.client.put(self.url, {"first_name": "X", "last_name": "Y"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
