from django.test import TestCase
from django.urls import reverse


class HealthViewTests(TestCase):
    def test_health_returns_ok(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class ApiExceptionHandlerTests(TestCase):
    def test_business_errors_are_mapped_to_detail_and_code(self):
        from rest_framework.exceptions import NotFound

        from .exceptions import BusinessError, BusinessNotFound, api_exception_handler

        cases = [
            (BusinessError("Нет в наличии", code="insufficient_stock"), 400, "insufficient_stock"),
            (BusinessNotFound("Нет в корзине", code="not_in_cart"), 404, "not_in_cart"),
            (BusinessError("Что-то"), 400, "business_error"),
        ]
        for exc, status_code, code in cases:
            with self.subTest(code=code):
                response = api_exception_handler(exc, {})
                self.assertEqual(response.status_code, status_code)
                self.assertEqual(response.data, {"detail": exc.message, "code": code})

        # стандартные ошибки DRF обрабатываются как раньше
        self.assertEqual(api_exception_handler(NotFound(), {}).status_code, 404)
        # прочие исключения не перехватываются (→ 500 и traceback в логах)
        self.assertIsNone(api_exception_handler(ValueError("boom"), {}))
