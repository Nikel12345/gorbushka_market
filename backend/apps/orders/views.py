from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.shops.mixins import SellerShopMixin

from .filters import OrderFilter
from .models import Order
from .pagination import OrderHistoryPagination
from .serializers import BuyerOrderSerializer, SellerOrderSerializer


class OrderFilterMixin:
    """Подключает единый OrderFilter к любому списку заказов."""

    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter


class SellerOrderListView(OrderFilterMixin, SellerShopMixin, generics.ListAPIView):
    """
    История заказов магазина, новые сверху. Фильтры — OrderFilter.
    Пагинация постраничная (?page=N): кабинет показывает таблицу со страницами.
    """

    serializer_class = SellerOrderSerializer

    def get_queryset(self):
        return Order.objects.filter(shop=self.get_shop()).with_details()


class BuyerOrderListView(OrderFilterMixin, generics.ListAPIView):
    """История заказов текущего пользователя: курсор, фильтры OrderFilter, сортировка."""

    permission_classes = [IsAuthenticated]
    serializer_class = BuyerOrderSerializer
    pagination_class = OrderHistoryPagination

    def get_queryset(self):
        return Order.objects.filter(buyer=self.request.user).with_details()
