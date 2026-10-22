from django_filters import rest_framework as filters

from apps.core.filters import BaseFilterSet

from .models import Order


class OrderFilter(BaseFilterSet):
    """
    Единые фильтры заказов: история в админке магазина, история
    покупателя и любые будущие списки заказов. Чьи заказы видны — задаёт view.
    """

    # ?status=new&status=confirmed — несколько значений (например, «активные»)
    status = filters.MultipleChoiceFilter(choices=Order.Status.choices, label="Статус")
    shop = filters.NumberFilter(field_name="shop_id", label="Магазин")
    date_from = filters.DateFilter(field_name="created_at", lookup_expr="date__gte", label="С даты")
    date_to = filters.DateFilter(field_name="created_at", lookup_expr="date__lte", label="По дату")

    range_fields = (("date_from", "date_to"),)

    class Meta:
        model = Order
        fields = ["status", "shop", "date_from", "date_to"]
