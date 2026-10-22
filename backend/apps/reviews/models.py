from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel

# Текст отзыва — три поля, нужно хотя бы одно
TEXT_FIELDS = ("pros", "cons", "comment")
TEXT_MAX_LENGTH = 2000
EMPTY_TEXT_MESSAGE = "Напишите достоинства, недостатки или комментарий."


class ReviewQuerySet(models.QuerySet):
    def with_details(self):
        """
        Всё, что выводят сериализаторы отзывов, одним запросом — и только это: от товара
        название, от автора имя и email (для админки), без полных строк товара и пользователя.
        """
        return self.select_related("product", "author").only(
            "id",
            "product_id",
            "author_id",
            "rating",
            *TEXT_FIELDS,
            "created_at",
            "updated_at",
            "product__title",
            "author__first_name",
            "author__email",
        )


class Review(TimeStampedModel):
    """
    Отзыв о товаре: оценка от 1 до 5 и текст — достоинства, недостатки, комментарий.
    Один отзыв от пользователя на товар; автор может его изменить или удалить, сотрудник — удалить.
    Отзыв относится к конкретному товару (варианту), а не к группе вариантов.
    Оценку и число отзывов товара (Product.rating, reviews_count) пересчитывает reviews.services.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", verbose_name="товар")
    # PROTECT: удаление пользователя молча меняло бы оценки товаров — сначала удаляют его отзывы
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews",
        verbose_name="автор",
    )
    rating = models.PositiveSmallIntegerField("оценка", validators=[MinValueValidator(1), MaxValueValidator(5)])
    pros = models.TextField("достоинства", max_length=TEXT_MAX_LENGTH, blank=True)
    cons = models.TextField("недостатки", max_length=TEXT_MAX_LENGTH, blank=True)
    comment = models.TextField("комментарий", max_length=TEXT_MAX_LENGTH, blank=True)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        verbose_name = "отзыв"
        verbose_name_plural = "отзывы"
        ordering = ["-created_at", "-id"]
        indexes = [
            # Под сортировки отзывов товара (keyset-пагинация по полю + id): новые сверху и по оценке
            # (rating_asc читает тот же индекс в обратную сторону)
            models.Index(fields=["product", "-created_at", "-id"], name="reviews_product_new_idx"),
            models.Index(fields=["product", "-rating", "-id"], name="reviews_product_rating_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "author"],
                name="reviews_one_per_author",
                violation_error_message="Этот пользователь уже оставил отзыв на товар.",
            ),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="reviews_rating_range"),
            models.CheckConstraint(
                condition=~models.Q(pros="", cons="", comment=""),
                name="reviews_has_text",
                violation_error_message=EMPTY_TEXT_MESSAGE,
            ),
        ]

    def __str__(self):
        return f"Отзыв #{self.pk} на «{self.product}»"
