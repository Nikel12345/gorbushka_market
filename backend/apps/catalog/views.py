from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.delivery.models import DeliveryMethod
from apps.shops.mixins import ShopAdminMixin

from . import accessories, services
from .categories import CategoryTree
from .filters import CharacteristicFilter, ProductFilter, ProductGroupFilter
from .models import Category, Characteristic, Product, ProductGroup
from .pagination import ProductFeedPagination
from .serializers import (
    AccessoryCardSerializer,
    AccessoryListSerializer,
    CategorySerializer,
    CharacteristicSerializer,
    CharacteristicValueSerializer,
    ProductAdminSerializer,
    ProductCardSerializer,
    ProductGroupSerializer,
    ProductImageSerializer,
    ProductPublicDetailSerializer,
)


class ProductFilterMixin:
    """Подключает единый ProductFilter к любому списку товаров."""

    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter


# --- Админка магазина ---


class ProductAdminListCreateView(ProductFilterMixin, ShopAdminMixin, generics.ListCreateAPIView):
    """GET — товары на продаже (те же фильтры, что в ленте), POST — добавить товар в магазин."""

    serializer_class = ProductAdminSerializer

    def get_queryset(self):
        return Product.objects.on_sale().with_admin_details()

    def perform_create(self, serializer):
        serializer.save(shop=self.get_shop())


class ProductAdminDetailView(ShopAdminMixin, generics.RetrieveUpdateDestroyAPIView):
    """GET — товар, PATCH — изменить (JSON или multipart с картинкой), DELETE — снять с продажи."""

    serializer_class = ProductAdminSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Product.objects.on_sale().with_admin_details()

    def perform_destroy(self, instance):
        services.archive_product(instance)


class ProductAdminMixin(ShopAdminMixin):
    """Для view, вложенных в /admin/products/<product_id>/... Снятый с продажи товар — 404."""

    product_url_kwarg = "product_id"

    def get_product(self) -> Product:
        if not hasattr(self, "_product"):
            self._product = get_object_or_404(Product.objects.on_sale(), pk=self.kwargs[self.product_url_kwarg])
        return self._product


class ProductImageAdminListCreateView(ProductAdminMixin, generics.ListCreateAPIView):
    """GET — фото товара по порядку, POST — загрузить одно фото (multipart, поле image) в конец."""

    serializer_class = ProductImageSerializer
    pagination_class = None

    def get_queryset(self):
        return self.get_product().images.all()

    def perform_create(self, serializer):
        serializer.save(product=self.get_product())


class ProductImageAdminDetailView(ProductAdminMixin, generics.DestroyAPIView):
    """DELETE — удалить фото. Если это была обложка, ей станет следующее фото."""

    def get_queryset(self):
        return self.get_product().images.all()

    def perform_destroy(self, instance):
        services.delete_image(instance)


class ProductImageOrderSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class ProductImageAdminOrderView(ProductAdminMixin, APIView):
    """PUT {"ids": [...]} — новый порядок всех фото товара, первое станет обложкой."""

    def put(self, request, *args, **kwargs):
        serializer = ProductImageOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        images = services.reorder_images(self.get_product(), serializer.validated_data["ids"])
        return Response(ProductImageSerializer(images, many=True, context={"request": request}).data)


class AccessoryListMixin:
    """Аксессуары товара на продаже по порядку списка (catalog/accessories.py)."""

    serializer_class = AccessoryCardSerializer
    pagination_class = None

    def accessories_queryset(self, product: Product):
        return accessories.accessories_of(product).select_related("shop", "category")


class ProductAccessoryAdminView(AccessoryListMixin, ProductAdminMixin, generics.ListAPIView):
    """
    GET — аксессуары товара (у товара группы вариантов — общие для всей группы),
    PUT {"ids": [...]} — заменить список целиком, в этом порядке ([] — убрать все) → новый список.
    """

    def get_queryset(self):
        return self.accessories_queryset(self.get_product())

    def put(self, request, *args, **kwargs):
        serializer = AccessoryListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_accessories(self.get_product(), serializer.validated_data["ids"])
        return self.list(request, *args, **kwargs)


# --- Категории ---


class CategoryListMixin:
    """Все категории плоским списком в порядке дерева: родитель, затем его подкатегории."""

    serializer_class = CategorySerializer
    pagination_class = None

    def list(self, request, *args, **kwargs):
        tree = CategoryTree.load()
        context = {**self.get_serializer_context(), "category_tree": tree}
        categories = [category for category, _ in tree.walk()]
        return Response(CategorySerializer(categories, many=True, context=context).data)


class CategoryAdminListCreateView(CategoryListMixin, generics.ListCreateAPIView):
    """GET — дерево категорий, POST — новая категория (parent_id — куда; без него — верхний уровень)."""

    permission_classes = [IsAdminUser]
    queryset = Category.objects.all()


class CategoryAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET — категория, PATCH — название, адрес, порядок, перенос (parent_id),
    DELETE — только пустую (без подкатегорий и товаров на продаже).
    """

    permission_classes = [IsAdminUser]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def perform_destroy(self, instance):
        services.delete_category(instance)


class CategoryListView(CategoryListMixin, generics.ListAPIView):
    """Дерево категорий для меню каталога. Товары раздела — лента с ?category=<id>."""

    permission_classes = [AllowAny]


# --- Характеристики и группы вариантов (админка магазина) ---
# Переименование и удаление — в админке Django: значения уже стоят у товаров.


class CharacteristicAdminListCreateView(generics.ListCreateAPIView):
    """
    GET — характеристики со справочниками значений; ?category=<id> — только доступные
    товарам этой категории (общие, её и категорий выше). POST — новая характеристика.
    """

    permission_classes = [IsAdminUser]
    serializer_class = CharacteristicSerializer
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = CharacteristicFilter

    def get_queryset(self):
        return Characteristic.objects.select_related("category").prefetch_related("values")


class CharacteristicAdminDetailView(generics.RetrieveUpdateAPIView):
    """GET — характеристика, PATCH — название, порядок, категория (перенос не проверяется — см. Characteristic)."""

    permission_classes = [IsAdminUser]
    serializer_class = CharacteristicSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Characteristic.objects.select_related("category").prefetch_related("values")


class CharacteristicValueAdminCreateView(generics.CreateAPIView):
    """POST — новое значение в справочник характеристики («Розовый» для «Цвет»)."""

    permission_classes = [IsAdminUser]
    serializer_class = CharacteristicValueSerializer

    def get_characteristic(self) -> Characteristic:
        if not hasattr(self, "_characteristic"):
            self._characteristic = get_object_or_404(Characteristic, pk=self.kwargs["characteristic_id"])
        return self._characteristic

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "characteristic": self.get_characteristic()}

    def perform_create(self, serializer):
        serializer.save(characteristic=self.get_characteristic())


class ProductGroupAdminListCreateView(generics.ListCreateAPIView):
    """
    GET — группы вариантов: ?q= — поиск по названию, ?category=<id> — подходящие товарам
    этой категории (без категории, её и категорий выше). POST — новая группа.
    """

    permission_classes = [IsAdminUser]
    serializer_class = ProductGroupSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductGroupFilter

    def get_queryset(self):
        return ProductGroup.objects.select_related("category").prefetch_related("axes")


class ProductGroupAdminDetailView(generics.RetrieveUpdateAPIView):
    """
    GET — группа, PATCH — название, категория и оси. Товары группы — /admin/products/?group=<id>.
    Новые оси и категория должны подходить всем товарам группы на продаже, иначе 400.
    """

    permission_classes = [IsAdminUser]
    serializer_class = ProductGroupSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return ProductGroup.objects.select_related("category").prefetch_related("axes")


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


class ProductAccessoryListView(AccessoryListMixin, generics.ListAPIView):
    """Раздел «Аксессуары» на странице товара. Пусто — не заданы. Снятый с продажи товар — 404."""

    permission_classes = [AllowAny]

    def get_queryset(self):
        product = get_object_or_404(Product.objects.on_sale().only("id", "group_id"), pk=self.kwargs["product_id"])
        return self.accessories_queryset(product)


class ProductPublicDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductPublicDetailSerializer

    def get_queryset(self):
        return (
            Product.objects.on_sale()
            .select_related("shop", "category", "group")
            .prefetch_related("images", Prefetch("delivery_methods", queryset=DeliveryMethod.objects.active()))
            .with_characteristics()
        )
