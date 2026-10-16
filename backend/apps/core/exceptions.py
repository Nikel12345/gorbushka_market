from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class BusinessError(Exception):
    """
    Нарушение бизнес-правила в сервисном слое (нет остатка, товар недоступен и т.п.).
    Сервисы бросают его вместо HTTP-ошибок — так они не зависят от транспорта
    (API, админка, фоновые задачи). В API превращается в ответ api_exception_handler.
    """

    status_code = 400

    def __init__(self, message: str, code: str = "business_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class BusinessNotFound(BusinessError):
    """Объект, с которым сервис должен работать, не найден (например, товара нет в корзине)."""

    status_code = 404

    def __init__(self, message: str, code: str = "not_found"):
        super().__init__(message, code)


class BusinessConflict(BusinessError):
    """
    Данные, на которых клиент построил запрос, устарели (корзина изменилась,
    цена выросла). Клиенту нужно перечитать состояние и повторить.
    """

    status_code = 409

    def __init__(self, message: str, code: str = "conflict"):
        super().__init__(message, code)


def api_exception_handler(exc, context):
    """
    DRF EXCEPTION_HANDLER: ошибки бизнес-правил → {"detail": "...", "code": "..."}
    с кодом из status_code (400 / 404 / 409). Остальное — стандартная обработка DRF.
    """
    if isinstance(exc, BusinessError):
        return Response({"detail": exc.message, "code": exc.code}, status=exc.status_code)
    return drf_exception_handler(exc, context)
