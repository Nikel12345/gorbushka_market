from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.services import get_request_cart
from apps.delivery.models import DeliveryMethod
from apps.users.models import User
from apps.users.services import login_user

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
    GuestCheckoutRequestSerializer,
    MarketOrderSerializer,
    OrderAdminSerializer,
    OrderStatusChangeRequestSerializer,
    PurchaseSerializer,
)

Actor = OrderStatusChange.Actor


class OrderFilterMixin:
    """Подключает единый OrderFilter к любому списку заказов."""

    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter


class OrderAudienceMixin:
    """
    Участник, от имени которого смотрят и ведут заказы (магазин, покупатель, маркет).
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


# --- Админка магазина ---


class OrderAdminMixin(OrderAudienceMixin):
    """Заказы магазина. Доступ — сотрудники (is_staff), остальным 403. Статусы ведут от имени магазина."""

    permission_classes = [IsAdminUser]
    order_actor = Actor.SELLER
    serializer_class = OrderAdminSerializer

    def get_queryset(self):
        return Order.objects.with_details()


class OrderAdminListView(OrderFilterMixin, OrderAdminMixin, generics.ListAPIView):
    """
    История заказов магазина, новые сверху. Фильтры — OrderFilter.
    Пагинация постраничная (?page=N): админка показывает таблицу со страницами.
    """


class OrderAdminDetailView(OrderAdminMixin, generics.RetrieveAPIView):
    pass


class OrderAdminStatusView(OrderStatusChangeMixin, OrderAdminMixin, generics.GenericAPIView):
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


class CheckoutAccessMixin:
    """Оформление доступно и гостю — из его корзины по сессии; аккаунт он укажет при оформлении."""

    permission_classes = [AllowAny]

    # DRF проверяет CSRF только у вошедших — для гостя включаем явно (оформление гостя ещё и входит в аккаунт)
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def buyer(self) -> User | None:
        return self.request.user if self.request.user.is_authenticated else None


class CheckoutView(CheckoutAccessMixin, APIView):
    """
    GET  — страница оформления: позиции со способами доставки, недоступные позиции, способы оплаты.
    POST — оформить покупку. Ответ — покупка целиком (как /me/purchases/{id}/).
           Гость дополнительно передаёт email и password: вход в аккаунт с этой почтой или новый аккаунт;
           после оформления он уже вошёл.
    """

    def get_throttles(self):
        # Гость вводит пароль от аккаунта — лимит попыток, как у входа
        if self.request.method == "POST" and self.buyer() is None:
            self.throttle_scope = "auth"
        return super().get_throttles()

    def get(self, request):
        preview = checkout.get_checkout(get_request_cart(request), self.buyer())
        return Response(CheckoutPreviewSerializer(preview).data)

    def post(self, request):
        cart = get_request_cart(request)
        buyer = self.buyer()
        if buyer is not None:
            serializer = CheckoutRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            purchase = checkout.place_purchase(cart, buyer, **serializer.service_kwargs())
        else:
            serializer = GuestCheckoutRequestSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            purchase = checkout.place_guest_purchase(cart, **serializer.service_kwargs())
            # Остаток корзины гостя (что не вошло в покупку) при входе переходит в корзину аккаунта
            login_user(request, purchase.buyer)
        purchase = Purchase.objects.with_details().get(pk=purchase.pk)
        data = PurchaseSerializer(purchase, context={"order_actor": Actor.BUYER}).data
        return Response(data, status=status.HTTP_201_CREATED)


class CheckoutQuoteView(CheckoutAccessMixin, APIView):
    """POST — отправки и суммы для выбранных способов доставки. Ничего не сохраняет."""

    def post(self, request):
        serializer = CheckoutQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = checkout.quote(get_request_cart(request), self.buyer(), **serializer.service_kwargs())
        return Response(CheckoutPlanSerializer(plan).data)
