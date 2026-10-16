from django.conf import settings
from rest_framework import serializers

from apps.core.fields import ImageUrlField
from apps.core.validators import MaxFileSizeValidator
from apps.delivery.models import DeliveryMethod
from apps.delivery.serializers import DeliveryMethodSerializer
from apps.shops.serializers import ShopBriefSerializer

from . import services
from .models import Product, ProductImage


def product_image_field(**kwargs):
    """Загрузка одного фото товара: проверка, что это картинка, и лимит размера."""
    return ImageUrlField(validators=[MaxFileSizeValidator(setting="PRODUCT_IMAGE_MAX_BYTES")], **kwargs)


class ProductImageSerializer(serializers.ModelSerializer):
    """Фото товара. Чтение — {id, url}; загрузка — файл в поле image (multipart)."""

    url = ImageUrlField(source="image", read_only=True)
    image = product_image_field(write_only=True, required=True, allow_null=False)

    class Meta:
        model = ProductImage
        fields = ["id", "url", "image"]

    def create(self, validated_data):
        # product приходит из view через serializer.save(product=...)
        return services.add_images(validated_data["product"], [validated_data["image"]])[0]


class ProductImagesField(serializers.ListField):
    """
    Фото товара в его сериализаторе. Чтение — все фото по порядку [{id, url}], первое — обложка.
    Запись — файлы (повторяющееся поле в multipart), они добавляются в конец.
    """

    child = product_image_field(allow_null=False)

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_representation(self, images):
        return ProductImageSerializer(images.all(), many=True, context=self.context).data


class SellerProductSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    # Магазин товара — чтобы фронт мог сгруппировать общий список /seller/products/
    shop = ShopBriefSerializer(read_only=True)
    # Обложка (первое фото). Запись — старый способ с одной картинкой: файл заменяет
    # обложку, null убирает её. Новый способ — images и /images/.
    image = product_image_field()
    images = ProductImagesField()
    delivery_methods = DeliveryMethodSerializer(many=True, read_only=True)
    # Запись: список id способов (JSON-массив или повторяющееся поле в multipart).
    # Обязателен при создании; в PATCH, если передан, заменяет набор целиком.
    delivery_method_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        allow_empty=False,
        queryset=DeliveryMethod.objects.all(),
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "shop",
            "title",
            "description",
            "price",
            "quantity",
            "image",
            "images",
            "delivery_methods",
            "delivery_method_ids",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "shop", "status", "status_display", "created_at", "updated_at"]

    def validate_delivery_method_ids(self, methods):
        # shop кладёт в контекст SellerShopMixin
        shop = self.context["shop"]
        allowed = set(DeliveryMethod.objects.available_for_shop(shop).values_list("pk", flat=True))
        unavailable = [method.name for method in methods if method.pk not in allowed]
        if unavailable:
            raise serializers.ValidationError(f"Способы доставки недоступны: {', '.join(unavailable)}.")
        if not shop.address:
            need_address = [method.name for method in methods if method.needs_shop_address]
            if need_address:
                raise serializers.ValidationError(
                    f"Укажите адрес магазина, чтобы выбрать: {', '.join(need_address)}.",
                    code="shop_address_required",
                )
        return list(dict.fromkeys(methods))

    def validate_images(self, files):
        # Предварительная проверка для понятной ошибки поля; точная — в сервисе под блокировкой
        limit = settings.PRODUCT_IMAGES_MAX
        existing = self.instance.images.count() if self.instance else 0
        if existing + len(files) > limit:
            raise serializers.ValidationError(f"У товара может быть не больше {limit} фото.", code="too_many_images")
        return files

    def _to_service_kwargs(self, validated_data):
        if "delivery_method_ids" in validated_data:
            validated_data["delivery_methods"] = validated_data.pop("delivery_method_ids")
        return validated_data

    def create(self, validated_data):
        # shop приходит из view через serializer.save(shop=...)
        return services.create_product(**self._to_service_kwargs(validated_data))

    def update(self, instance, validated_data):
        return services.update_product(instance, **self._to_service_kwargs(validated_data))


class ProductCardSerializer(serializers.ModelSerializer):
    """Карточка товара в публичной ленте — без тяжёлых полей."""

    shop = ShopBriefSerializer(read_only=True)
    in_stock = serializers.SerializerMethodField()
    image = ImageUrlField(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "title", "price", "image", "in_stock", "shop", "created_at"]
        read_only_fields = fields

    def get_in_stock(self, product) -> bool:
        return product.quantity > 0


class ProductPublicDetailSerializer(ProductCardSerializer):
    delivery_methods = DeliveryMethodSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta(ProductCardSerializer.Meta):
        fields = [*ProductCardSerializer.Meta.fields, "description", "quantity", "images", "delivery_methods"]
        read_only_fields = fields
