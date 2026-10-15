from rest_framework import serializers

from apps.core.fields import ImageUrlField
from apps.core.validators import MaxFileSizeValidator
from apps.delivery.models import DeliveryMethod
from apps.delivery.serializers import DeliveryMethodSerializer
from apps.shops.serializers import ShopBriefSerializer

from . import services
from .models import Product


class SellerProductSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    # Магазин товара — чтобы фронт мог сгруппировать общий список /seller/products/
    shop = ShopBriefSerializer(read_only=True)
    image = ImageUrlField(validators=[MaxFileSizeValidator(setting="PRODUCT_IMAGE_MAX_BYTES")])
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
        allowed = set(DeliveryMethod.objects.available_for_shop(self.context["shop"]).values_list("pk", flat=True))
        unavailable = [method.name for method in methods if method.pk not in allowed]
        if unavailable:
            raise serializers.ValidationError(f"Способы доставки недоступны: {', '.join(unavailable)}.")
        return list(dict.fromkeys(methods))

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

    class Meta(ProductCardSerializer.Meta):
        fields = [*ProductCardSerializer.Meta.fields, "description", "quantity", "delivery_methods"]
        read_only_fields = fields
