"""
Отзывы. Любое изменение отзывов (API, админка Django) идёт через эти функции:
они пересчитывают кеш оценки товара — Product.rating и reviews_count.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Avg, Count

from apps.catalog.models import Product
from apps.core.exceptions import BusinessError

from .models import Review


def refresh_rating(*product_ids) -> None:
    """
    Пересчитывает оценку и число отзывов товаров по их отзывам. Вызывается в транзакции,
    изменившей отзывы: блокировка товара ставит параллельные изменения в очередь,
    и последний пересчёт видит все отзывы.
    """
    ids = {pk for pk in product_ids if pk is not None}
    for product in Product.objects.select_for_update().filter(pk__in=ids).order_by("pk"):
        stats = Review.objects.filter(product=product).aggregate(avg=Avg("rating"), count=Count("id"))
        product.rating = Decimal(str(stats["avg"] or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        product.reviews_count = stats["count"]
        product.save(update_fields=["rating", "reviews_count"])


@transaction.atomic
def create_review(*, product: Product, author, rating: int, pros="", cons="", comment="") -> Review:
    # Под блокировкой товара: два одновременных отзыва одного автора не пройдут проверку оба
    Product.objects.select_for_update().get(pk=product.pk)
    if Review.objects.filter(product=product, author=author).exists():
        raise BusinessError("Вы уже оставили отзыв на этот товар — его можно изменить.", code="review_exists")
    review = Review.objects.create(
        product=product, author=author, rating=rating, pros=pros, cons=cons, comment=comment
    )
    refresh_rating(product.pk)
    return review


def update_review(review: Review, **fields) -> Review:
    """Оценка и текст. Товар и автор у отзыва не меняются."""
    for name, value in fields.items():
        setattr(review, name, value)
    return save_review(review)


@transaction.atomic
def save_review(review: Review, *, previous_product_id=None) -> Review:
    """
    Сохраняет уже проверенный отзыв (сериализатор, форма админки Django) и пересчитывает
    оценку его товара — и прежнего, если в админке Django отзыв перенесли на другой товар.
    """
    review.save()
    refresh_rating(review.product_id, previous_product_id)
    return review


@transaction.atomic
def delete_reviews(reviews) -> None:
    """Удаляет отзывы (queryset) и пересчитывает оценки их товаров."""
    product_ids = set(reviews.values_list("product_id", flat=True))
    reviews.delete()
    refresh_rating(*product_ids)


def delete_review(review: Review) -> None:
    delete_reviews(Review.objects.filter(pk=review.pk))
