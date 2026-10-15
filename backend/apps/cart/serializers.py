from rest_framework import serializers

from apps.catalog.serializers import ProductCardSerializer

MAX_QUANTITY = 999


class CartLineSerializer(serializers.Serializer):
    # Та же карточка, что в ленте: id, title, price, image, in_stock, shop
    product = ProductCardSerializer(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)


class CartSerializer(serializers.Serializer):
    items = CartLineSerializer(source="lines", many=True, read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    has_unavailable = serializers.BooleanField(read_only=True)


class CartAddSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY, default=1)


class CartQuantitySerializer(serializers.Serializer):
    # 0 — убрать товар из корзины
    quantity = serializers.IntegerField(min_value=0, max_value=MAX_QUANTITY)
