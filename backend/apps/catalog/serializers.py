from rest_framework import serializers

from apps.shops.serializers import ShopBriefSerializer

from . import services
from .models import Product


class SellerProductSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "description",
            "price",
            "quantity",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "status_display", "created_at", "updated_at"]

    def create(self, validated_data):
        # shop приходит из view через serializer.save(shop=...)
        return services.create_product(**validated_data)


class ProductCardSerializer(serializers.ModelSerializer):
    """Карточка товара в публичной ленте — без тяжёлых полей."""

    shop = ShopBriefSerializer(read_only=True)
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "title", "price", "in_stock", "shop", "created_at"]
        read_only_fields = fields

    def get_in_stock(self, product) -> bool:
        return product.quantity > 0


class ProductPublicDetailSerializer(ProductCardSerializer):
    class Meta(ProductCardSerializer.Meta):
        fields = [*ProductCardSerializer.Meta.fields, "description", "quantity"]
        read_only_fields = fields
