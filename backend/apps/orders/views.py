from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.delivery.models import DeliveryMethod
from apps.shops.mixins import SellerShopMixin

from . import checkout, statuses
from .filters import OrderFilter
from .models import Order, OrderStatusChange, Purchase
from .pagination import OrderHistoryPagination
from .serializers import (
    BuyerOrderSerializer,
    CheckoutPlanSerializer,
    CheckoutPreviewSerializer,
    CheckoutQuoteRequestSerializer,
    CheckoutRequestSerializer,
    MarketOrderSerializer,
    OrderStatusChangeRequestSerializer,
    PurchaseSerializer,
    SellerOrderSerializer,
)

Actor = OrderStatusChange.Actor


class OrderFilterMixin:
    """Подключает единый OrderFilter к любому списку заказов."""

    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter


class OrderAudienceMixin:
    """
    Участник, от имени которого смотрят и ведут заказы (продавец, покупатель, маркет).
    Чьи заказы видны — задаёт get_queryset аудитории; что можно сделать — orders.statuses.
    """

    order_actor: str

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "order_actor": self.order_actor}


class OrderStatusChangeMixin:
    """POST {"status": "..."} — перевести заказ; ответ — заказ с новыми available_statuses."""

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = OrderStatusChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        statuses.change_status(
            order, to=serializer.validated_data["status"], actor=self.order_actor, user=request.user
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=order.pk)).data)


# --- Кабинет продавца ---


class SellerOrdersMixin(OrderAudienceMixin, SellerShopMixin):
    order_actor = Actor.SELLER
    serializer_class = SellerOrderSerializer

    def get_queryset(self):
        return Order.objects.filter(shop=self.get_shop()).with_details()


class SellerOrderListView(OrderFilterMixin, SellerOrdersMixin, generics.ListAPIView):
    """
    История заказов магазина, новые сверху. Фильтры — OrderFilter.
    Пагинация постраничная (?page=N): кабинет показывает таблицу со страницами.
    """


class SellerOrderDetailView(SellerOrdersMixin, generics.RetrieveAPIView):
    pass


class SellerOrderStatusView(OrderStatusChangeMixin, SellerOrdersMixin, generics.GenericAPIView):
    pass


# --- Маркет (сотрудники: доставка курьером маркета) ---


class MarketOrdersMixin(OrderAudienceMixin):
    """Заказы, которые доставляет маркет. Доступ — сотрудники (is_staff); позже — роль курьера."""

    permission_classes = [IsAdminUser]
    order_actor = Actor.MARKET
    serializer_class = MarketOrderSerializer

    def get_queryset(self):
        return Order.objects.filter(
            shipment__delivery_method__provider=DeliveryMethod.Provider.MARKET
        ).with_details()


class MarketOrderListView(OrderFilterMixin, MarketOrdersMixin, generics.ListAPIView):
    """Заказы на доставку маркетом, новые сверху; ?status=ready — переданные курьеру."""


class MarketOrderStatusView(OrderStatusChangeMixin, MarketOrdersMixin, generics.GenericAPIView):
    pass


# --- Покупатель ---


class BuyerOrdersMixin(OrderAudienceMixin):
    permission_classes = [IsAuthenticated]
    order_actor = Actor.BUYER
    serializer_class = BuyerOrderSerializer

    def get_queryset(self):
        return Order.objects.filter(buyer=self.request.user).with_details()


class BuyerOrderListView(OrderFilterMixin, BuyerOrdersMixin, generics.ListAPIView):
    """История заказов текущего пользователя: курсор, фильтры OrderFilter, сортировка."""

    pagination_class = OrderHistoryPagination


class BuyerOrderDetailView(BuyerOrdersMixin, generics.RetrieveAPIView):
    pass


class BuyerOrderStatusView(OrderStatusChangeMixin, BuyerOrdersMixin, generics.GenericAPIView):
    """Покупатель может только отменить новый заказ."""


class BuyerPurchaseMixin(OrderAudienceMixin):
    """Покупки текущего пользователя: чужие не видны (404)."""

    permission_classes = [IsAuthenticated]
    order_actor = Actor.BUYER
    serializer_class = PurchaseSerializer

    def get_queryset(self):
        return Purchase.objects.filter(buyer=self.request.user).with_details()


class BuyerPurchaseListView(BuyerPurchaseMixin, generics.ListAPIView):
    """История покупок: курсор и сортировки — как у истории заказов."""

    pagination_class = OrderHistoryPagination


class BuyerPurchaseDetailView(BuyerPurchaseMixin, generics.RetrieveAPIView):
    pass


class CheckoutView(APIView):
    """
    GET  — страница оформления: позиции со способами доставки, недоступные позиции, способы оплаты.
    POST — оформить покупку. Ответ — покупка целиком (как /me/purchases/{id}/).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CheckoutPreviewSerializer(checkout.get_checkout(request.user)).data)

    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase = checkout.place_purchase(request.user, **serializer.service_kwargs())
        purchase = Purchase.objects.with_details().get(pk=purchase.pk)
        data = PurchaseSerializer(purchase, context={"order_actor": Actor.BUYER}).data
        return Response(data, status=status.HTTP_201_CREATED)


class CheckoutQuoteView(APIView):
    """POST — отправки и суммы для выбранных способов доставки. Ничего не сохраняет."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = checkout.quote(request.user, **serializer.service_kwargs())
        return Response(CheckoutPlanSerializer(plan).data)
