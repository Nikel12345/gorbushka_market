from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError


class BaseFilterSet(filters.FilterSet):
    """
    База для всех FilterSet проекта.

    Правило: один FilterSet на сущность (ProductFilter, OrderFilter, ...), и он
    переиспользуется всеми view этой сущности — публичными, кабинета продавца,
    страницы покупателя. Видимость данных (чьи заказы, какие товары) задаёт
    queryset view, а не фильтр.

    range_fields — пары (нижняя граница, верхняя граница), например
    ("price_min", "price_max"): если заданы обе и нижняя больше — 400.
    """

    range_fields: tuple[tuple[str, str], ...] = ()

    def filter_queryset(self, queryset):
        cleaned = self.form.cleaned_data
        for low, high in self.range_fields:
            low_value, high_value = cleaned.get(low), cleaned.get(high)
            if low_value is not None and high_value is not None and low_value > high_value:
                raise ValidationError({low: [f"Не может быть больше {high}."]})
        return super().filter_queryset(queryset)
