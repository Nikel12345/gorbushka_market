from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.delivery.models import DeliveryMethod
from apps.shops.mixins import SellerShopMixin
from apps.shops.models import Shop

from . import services
from .filters import ProductFilter
from .models import Product
from .pagination import ProductFeedPagination
from .serializers import (
    ProductCardSerializer,
    ProductImageSerializer,
    ProductPublicDetailSerializer,
    SellerProductSerializer,
)


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


class SellerProductMixin(SellerShopMixin):
    """Для view, вложенных в /seller/shops/<shop_id>/products/<product_id>/... Чужой товар — 404."""

    product_url_kwarg = "product_id"

    def get_product(self) -> Product:
        if not hasattr(self, "_product"):
            self._product = get_object_or_404(
                Product.objects.filter(shop=self.get_shop()).on_sale(),
                pk=self.kwargs[self.product_url_kwarg],
            )
        return self._product


class SellerProductImageListCreateView(SellerProductMixin, generics.ListCreateAPIView):
    """GET — фото товара по порядку, POST — загрузить одно фото (multipart, поле image) в конец."""

    serializer_class = ProductImageSerializer
    pagination_class = None

    def get_queryset(self):
        return self.get_product().images.all()

    def perform_create(self, serializer):
        serializer.save(product=self.get_product())


class SellerProductImageDetailView(SellerProductMixin, generics.DestroyAPIView):
    """DELETE — удалить фото. Если это была обложка, ей станет следующее фото."""

    def get_queryset(self):
        return self.get_product().images.all()

    def perform_destroy(self, instance):
        services.delete_image(instance)


class ProductImageOrderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class SellerProductImageOrderView(SellerProductMixin, APIView):
    """PUT {"ids": [...]} — новый порядок всех фото товара, первое станет обложкой."""

    def put(self, request, *args, **kwargs):
        serializer = ProductImageOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        images = services.reorder_images(self.get_product(), serializer.validated_data["ids"])
        return Response(ProductImageSerializer(images, many=True, context={"request": request}).data)


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
            "images", Prefetch("delivery_methods", queryset=DeliveryMethod.objects.active())
        )
