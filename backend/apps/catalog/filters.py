from django.db.models import Q
from django_filters import rest_framework as filters

from apps.core.filters import BaseFilterSet
from apps.currency.services import usd_below, usd_from

from .categories import CategoryTree
from .models import Characteristic, Product, ProductGroup
from .search import normalize, search_products

MAX_QUERY_LENGTH = 200


class ProductFilter(BaseFilterSet):
    """
    Единые фильтры товаров: публичная лента, админка магазина и любые будущие
    списки товаров. Новые фильтры (категория, характеристики) добавляются сюда.
    """

    q = filters.CharFilter(method="filter_search", label="Поиск")
    shop = filters.NumberFilter(field_name="shop_id", label="Магазин")
    category = filters.NumberFilter(method="filter_category", label="Категория (вместе с подкатегориями)")
    # В рублях, как цена на витрине; в базе цена в долларах — границы переводятся по курсу
    price_min = filters.NumberFilter(method="filter_price_min", label="Цена от, ₽")
    price_max = filters.NumberFilter(method="filter_price_max", label="Цена до, ₽")
    in_stock = filters.BooleanFilter(method="filter_in_stock", label="Только в наличии")
    delivery_method = filters.NumberFilter(field_name="delivery_methods", label="Способ доставки")
    group = filters.NumberFilter(field_name="group_id", label="Группа вариантов")

    range_fields = (("price_min", "price_max"),)

    class Meta:
        model = Product
        fields = ["q", "shop", "category", "price_min", "price_max", "in_stock", "delivery_method", "group"]

    def filter_search(self, queryset, name, value):
        return search_products(queryset, value[:MAX_QUERY_LENGTH])

    def filter_category(self, queryset, name, value):
        return queryset.filter(category_id__in=CategoryTree.load().subtree_ids(int(value)))

    def filter_price_min(self, queryset, name, value):
        return queryset.filter(price_usd__gte=usd_from(value))

    def filter_price_max(self, queryset, name, value):
        return queryset.filter(price_usd__lt=usd_below(value))

    def filter_in_stock(self, queryset, name, value):
        if value is True:
            return queryset.filter(quantity__gt=0)
        if value is False:
            return queryset.filter(quantity=0)
        return queryset


def available_in_category(queryset, category_id: int):
    """Характеристики и группы, подходящие товарам категории: без категории, её и категорий выше."""
    path = [category.id for category in CategoryTree.load().path(category_id)]
    return queryset.filter(Q(category__isnull=True) | Q(category_id__in=path))


class ProductGroupFilter(BaseFilterSet):
    q = filters.CharFilter(method="filter_search", label="Поиск по названию")
    category = filters.NumberFilter(method="filter_category", label="Подходят товарам категории")

    class Meta:
        model = ProductGroup
        fields = ["q", "category"]

    def filter_category(self, queryset, name, value):
        return available_in_category(queryset, int(value))

    def filter_search(self, queryset, name, value):
        # Групп немного, а LIKE в SQLite не понимает регистр кириллицы — фильтруем в Python
        terms = normalize(value[:MAX_QUERY_LENGTH]).split()
        ids = [pk for pk, title in queryset.values_list("id", "name") if all(t in normalize(title) for t in terms)]
        return queryset.filter(pk__in=ids)


class CharacteristicFilter(BaseFilterSet):
    category = filters.NumberFilter(method="filter_category", label="Доступные в категории")

    class Meta:
        model = Characteristic
        fields = ["category"]

    def filter_category(self, queryset, name, value):
        return available_in_category(queryset, int(value))
