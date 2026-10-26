from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """
    Собственная модель пользователя. Вход — по email, username не используется.
    Покупатель и продавец пока не различаются: роли/профили будут добавляться
    отдельными полями или связанными моделями обычными миграциями.
    """

    username = None
    email = models.EmailField("email", unique=True)
    # Для связи по заказам. Хранится нормализованным: +79991234567 (см. serializers.PhoneField)
    phone = models.CharField("телефон", max_length=20, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)
