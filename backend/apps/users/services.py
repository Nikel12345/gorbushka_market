"""
Бизнес-логика пользователей. View и сериализаторы только валидируют вход
и вызывают функции отсюда — так логику легко переиспользовать (API, админка,
management-команды, фоновые задачи) и оборачивать в транзакции.
"""
from django.contrib.auth import authenticate, login, logout
from django.db import transaction

from .models import User


@transaction.atomic
def register_user(*, email: str, password: str, first_name: str = "", last_name: str = "") -> User:
    # Здесь же в будущем: создание профиля, отправка письма подтверждения и т.п.
    return User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )


def authenticate_user(request, *, email: str, password: str) -> User | None:
    return authenticate(request, email=email, password=password)


def login_user(request, user: User) -> None:
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")


def logout_user(request) -> None:
    logout(request)


def update_profile(user: User, **fields) -> User:
    for name, value in fields.items():
        setattr(user, name, value)
    user.save(update_fields=list(fields))
    return user
