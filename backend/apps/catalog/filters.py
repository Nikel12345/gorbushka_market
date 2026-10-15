from django_filters import rest_framework as filters

from apps.core.filters import BaseFilterSet

from .models import Product
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
