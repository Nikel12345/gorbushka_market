class BusinessError(Exception):
    """
    Нарушение бизнес-правила в сервисном слое (нет остатка, товар недоступен и т.п.).
    Сервисы бросают его вместо HTTP-ошибок — так они не зависят от транспорта
    (API, админка, фоновые задачи). В API-слое его следует превращать в 400.
    """

    def __init__(self, message: str, code: str = "business_error"):
        super().__init__(message)
        self.message = message
        self.code = code
