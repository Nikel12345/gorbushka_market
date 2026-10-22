from django_filters import rest_framework as filters

from apps.core.filters import BaseFilterSet

from .models import Review


class ReviewFilter(BaseFilterSet):
    """Единые фильтры отзывов: витрина, «мои отзывы», админка. Чьи отзывы видны — задаёт view."""

    product = filters.NumberFilter(field_name="product_id", label="Товар")
    # ?rating=5&rating=4 — несколько оценок
    rating = filters.MultipleChoiceFilter(choices=[(n, str(n)) for n in range(1, 6)], label="Оценка")

    class Meta:
        model = Review
        fields = ["product", "rating"]
