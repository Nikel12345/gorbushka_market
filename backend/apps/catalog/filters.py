from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError

from apps.core.filters import BaseFilterSet

from .models import Product
from .pagination import ProductFeedPagination
from .search import search_products

MAX_QUERY_LENGTH = 200


class ProductFilter(BaseFilterSet):
    """
    Единые фильтры товаров: публичная лента, кабинет продавца и любые будущие
    списки товаров. Новые фильтры (категория, характеристики) добавляются сюда.
    """

    q = filters.CharFilter(method="filter_search", label="Поиск")
    shop = filters.NumberFilter(field_name="shop_id", label="Магазин")
    price_min = filters.NumberFilter(field_name="price", lookup_expr="gte", label="Цена от")
    price_max = filters.NumberFilter(field_name="price", lookup_expr="lte", label="Цена до")
    in_stock = filters.BooleanFilter(method="filter_in_stock", label="Только в наличии")
    delivery_method = filters.NumberFilter(field_name="delivery_methods", label="Способ доставки")

    range_fields = (("price_min", "price_max"),)

    class Meta:
        model = Product
        fields = ["q", "shop", "price_min", "price_max", "in_stock", "delivery_method"]

    def filter_search(self, queryset, name, value):
        return search_products(queryset, value[:MAX_QUERY_LENGTH])

    def filter_in_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(quantity__gt=0)
        if value is False:
            return queryset.filter(quantity=0)
        return queryset


def clean_feed_params(params, *, exclude=()) -> dict[str, str]:
    """
    Проверяет сохранённые параметры ленты — фильтры ProductFilter и sort — например,
    для ссылки из рекламы на магазин. Правила те же, что у ленты, ошибки — Django
    ValidationError (для форм и админки). Возвращает значения строками, как в адресе:
    фронт кладёт их в query string как есть.
    """
    if not isinstance(params, dict):
        raise DjangoValidationError("Нужен объект {параметр: значение}.")
    allowed = [name for name in [*ProductFilter.base_filters, "sort"] if name not in exclude]
    unknown = [name for name in params if name not in allowed]
    if unknown:
        raise DjangoValidationError(
            f"Неизвестные параметры: {', '.join(unknown)}. Допустимые: {', '.join(allowed)}."
        )

    normalized = {}
    for name, value in params.items():
        if isinstance(value, bool):
            value = "true" if value else "false"
        elif not isinstance(value, (str, int, float)):
            raise DjangoValidationError(f"{name}: значение должно быть строкой, числом или true/false.")
        normalized[name] = str(value)

    sort_options = ProductFeedPagination.sort_options
    if "sort" in normalized and normalized["sort"] not in sort_options:
        raise DjangoValidationError(f"sort: допустимые значения — {', '.join(sort_options)}.")
    filterset = ProductFilter(data=normalized, queryset=Product.objects.none())
    if not filterset.is_valid():
        raise DjangoValidationError(
            "; ".join(f"{name}: {' '.join(errors)}" for name, errors in filterset.errors.items())
        )
    try:
        filterset.qs  # range_fields и прочие проверки, которые делает filter_queryset
    except ValidationError as error:
        raise DjangoValidationError(
            "; ".join(f"{name}: {' '.join(map(str, errors))}" for name, errors in error.detail.items())
        ) from error
    return normalized
