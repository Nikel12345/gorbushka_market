from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.delivery.models import DeliveryMethod
from apps.shops.mixins import SellerShopMixin
from apps.shops.models import Shop

from . import services
from .filters import ProductFilter
from .models import Product
from .pagination import ProductFeedPagination
from .serializers import ProductCardSerializer, ProductPublicDetailSerializer, SellerProductSerializer


class ProductFilterMixin:
    """Подключает единый ProductFilter к любому списку товаров."""

    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter


# --- Кабинет продавца ---


class SellerAllProductsView(ProductFilterMixin, generics.ListAPIView):
    """
    Все товары на продаже во всех магазинах продавца — для страницы товаров,
    где фронт группирует их по магазинам. Отсортированы по магазину (в порядке
    /seller/shops/), внутри — новые сверху. Фильтры — общий ProductFilter.
    Без пагинации: отдаётся весь список.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SellerProductSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Product.objects.filter(shop__in=Shop.objects.managed_by(self.request.user))
            .on_sale()
            .with_seller_details()
            .order_by("shop_id", "-created_at", "-id")
        )


class SellerProductListCreateView(ProductFilterMixin, SellerShopMixin, generics.ListCreateAPIView):
    """GET — товары магазина на продаже (те же фильтры, что в ленте), POST — добавить товар."""

    serializer_class = SellerProductSerializer

    def get_queryset(self):
        return Product.objects.filter(shop=self.get_shop()).on_sale().with_seller_details()

    def perform_create(self, serializer):
        serializer.save(shop=self.get_shop())


class SellerProductDetailView(SellerShopMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET — товар, PATCH — изменить (JSON или multipart с картинкой), DELETE — снять с продажи.
    Владение проверяет SellerShopMixin: магазин должен быть managed_by(user),
    а товар — из этого магазина; иначе 404.
    """

    serializer_class = SellerProductSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Product.objects.filter(shop=self.get_shop()).on_sale().with_seller_details()

    def perform_destroy(self, instance):
        services.archive_product(instance)


# --- Публичное ---


class ProductFeedView(ProductFilterMixin, generics.ListAPIView):
    """
    Публичная лента товаров главной страницы: фильтры, поиск, сортировка,
    бесконечная прокрутка по курсору (см. apps/core/pagination.py).
    """

    permission_classes = [AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = ProductFeedPagination

    def get_queryset(self):
        return Product.objects.on_sale().select_related("shop")


class ProductPublicDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductPublicDetailSerializer

    def get_queryset(self):
        return Product.objects.on_sale().select_related("shop").prefetch_related(
            Prefetch("delivery_methods", queryset=DeliveryMethod.objects.active())
        )
