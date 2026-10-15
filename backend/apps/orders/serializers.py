from rest_framework import serializers

from apps.shops.serializers import ShopBriefSerializer
from apps.users.models import User

from .models import Order, OrderItem


class OrderBuyerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


class OrderItemSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "title", "price", "quantity", "total"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """Общая часть заказа для всех сторон. Наследники добавляют свои поля."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "status_display", "total_amount", "items", "created_at", "updated_at"]
        read_only_fields = fields


class SellerOrderSerializer(OrderSerializer):
    """Продавцу важно, кто купил."""

    buyer = OrderBuyerSerializer(read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = [*OrderSerializer.Meta.fields, "buyer"]
        read_only_fields = fields


class BuyerOrderSerializer(OrderSerializer):
    """Покупателю важно, где купил."""

    shop = ShopBriefSerializer(read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = [*OrderSerializer.Meta.fields, "shop"]
        read_only_fields = fields
