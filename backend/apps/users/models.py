from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Собственная модель пользователя.
    Заведена сразу: заменить AUTH_USER_MODEL после первых миграций очень
    дорого, а расширять свою модель (роли, продавец/покупатель, телефон и т.д.)
    можно в любой момент обычными миграциями.
    """

    class Meta(AbstractUser.Meta):
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
