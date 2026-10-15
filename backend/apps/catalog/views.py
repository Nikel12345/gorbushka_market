from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.shops.mixins import SellerShopMixin

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


class SellerProductListCreateView(ProductFilterMixin, SellerShopMixin, generics.ListCreateAPIView):
    """GET — товары магазина на продаже (те же фильтры, что в ленте), POST — добавить товар."""

    serializer_class = SellerProductSerializer

    def get_queryset(self):
        return Product.objects.filter(shop=self.get_shop()).on_sale()

    def perform_create(self, serializer):
        serializer.save(shop=self.get_shop())


class SellerProductDetailView(SellerShopMixin, generics.RetrieveDestroyAPIView):
    """GET — товар, DELETE — снять с продажи."""

    serializer_class = SellerProductSerializer

    def get_queryset(self):
        return Product.objects.filter(shop=self.get_shop()).on_sale()

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
        return Product.objects.on_sale().select_related("shop")
