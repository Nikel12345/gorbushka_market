import os
import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.delivery.models import DeliveryMethod
from apps.shops.models import Shop

from .search import build_search_text


def product_image_upload_to(instance, filename):
    # Случайное имя: без коллизий и без утечки исходных имён файлов пользователей
    ext = os.path.splitext(filename)[1].lower()
    return f"products/{uuid.uuid4().hex}{ext}"


class ProductQuerySet(models.QuerySet):
    def on_sale(self):
        return self.filter(status=Product.Status.ACTIVE)

    def with_seller_details(self):
        """Всё, что выводит кабинет продавца по товару, без N+1."""
        return self.select_related("shop").prefetch_related("delivery_methods")


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "На продаже"
        # Товар «удалён» продавцом. Физически не удаляем: на него ссылаются заказы.
        ARCHIVED = "archived", "Удалён"

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="магазин",
    )
    title = models.CharField("название", max_length=255)
    description = models.TextField("описание", blank=True)
    price = models.DecimalField(
        "цена",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    quantity = models.PositiveIntegerField("в наличии", default=1)
    image = models.ImageField("фото", upload_to=product_image_upload_to, blank=True, max_length=255)
    # Какими способами можно получить товар. Задаёт продавец при создании/редактировании,
    # из DeliveryMethod.objects.available_for_shop(shop).
    delivery_methods = models.ManyToManyField(
        DeliveryMethod,
        related_name="products",
        verbose_name="способы доставки",
        blank=True,
    )
    status = models.CharField(
        "статус",
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    # Нормализованный текст для поиска, заполняется в save(). См. catalog/search.py
    search_text = models.TextField(editable=False, blank=True, default="")

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["shop", "status"]),
            # Под сортировки публичной ленты (keyset-пагинация по полю + id)
            models.Index(fields=["status", "-created_at", "-id"], name="catalog_feed_new_idx"),
            models.Index(fields=["status", "price", "id"], name="catalog_feed_price_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gt=0), name="catalog_product_price_positive"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.search_text = build_search_text(self.title, self.description)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and {"title", "description"} & set(update_fields):
            kwargs["update_fields"] = {*update_fields, "search_text"}
        super().save(*args, **kwargs)
