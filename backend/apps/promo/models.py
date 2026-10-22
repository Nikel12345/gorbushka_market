import os
import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_site_link


def promo_image_upload_to(instance, filename):
    # Случайное имя, как у фото товаров. Без слов ad/banner в пути — их режут блокировщики рекламы
    ext = os.path.splitext(filename)[1].lower()
    return f"promo/{uuid.uuid4().hex}{ext}"


class PromoQuerySet(models.QuerySet):
    def live(self, now=None):
        """Включённые и в периоде показа."""
        now = now or timezone.now()
        return self.filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gt=now),
            is_active=True,
        )


class Promo(TimeStampedModel):
    """
    Рекламная полоса. Для какого раздела — placement. API отдаёт случайную из показываемых,
    куда и когда её вставить, решает фронт (см. FeedPromoView).
    """

    class Placement(models.TextChoices):
        FEED = "feed", "Лента на главной"

    placement = models.CharField("где показывать", max_length=30, choices=Placement.choices, default=Placement.FEED)
    title = models.CharField("название", max_length=255, help_text="Для админки и alt-текста картинки")
    image = models.ImageField("картинка", upload_to=promo_image_upload_to, max_length=255)
    image_mobile = models.ImageField(
        "картинка для телефона",
        upload_to=promo_image_upload_to,
        max_length=255,
        blank=True,
        help_text="Узкая версия. Если нет — показывается основная.",
    )
    # Куда ведёт полоса. Пусто — никуда.
    url = models.CharField(
        "ссылка",
        max_length=500,
        blank=True,
        validators=[validate_site_link],
        help_text="Путь на сайте (/products/7, /?q=чехол) или полный адрес https://...",
    )
    position = models.PositiveIntegerField("порядок", default=0)
    is_active = models.BooleanField("показывать", default=True)
    starts_at = models.DateTimeField("показывать с", null=True, blank=True)
    ends_at = models.DateTimeField("показывать до", null=True, blank=True)

    objects = PromoQuerySet.as_manager()

    class Meta:
        verbose_name = "реклама"
        verbose_name_plural = "реклама"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["placement", "is_active", "position", "id"], name="promo_live_idx")]
        constraints = [
            models.CheckConstraint(
                condition=Q(starts_at__isnull=True) | Q(ends_at__isnull=True) | Q(ends_at__gt=models.F("starts_at")),
                name="promo_period_valid",
                violation_error_message="«Показывать до» должно быть позже «Показывать с».",
            ),
        ]

    def __str__(self):
        return self.title
