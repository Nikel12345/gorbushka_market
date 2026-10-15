from rest_framework import serializers

from apps.users.serializers import UserSerializer

from . import services
from .models import Shop


class ShopBriefSerializer(serializers.ModelSerializer):
    """Магазин в чужих ответах: карточка товара, заказ, профиль продавца."""

    class Meta:
        model = Shop
        fields = ["id", "name"]
        read_only_fields = fields


class ShopPublicSerializer(serializers.ModelSerializer):
    """
    Страница магазина для покупателя. Сюда — всё, что видно публично
    (логотип, контакты, адрес на рынке, рейтинг...).
    """

    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Shop
        fields = ["id", "name", "description", "address", "products_count", "created_at"]
        read_only_fields = fields

    def get_products_count(self, shop) -> int:
        # Аннотируется ShopQuerySet.with_stats(); запасной вариант — для только что созданного
        count = getattr(shop, "products_count", None)
        if count is None:
            from apps.catalog.models import Product

            count = shop.products.filter(status=Product.Status.ACTIVE).count()
        return count


class SellerShopSerializer(ShopPublicSerializer):
    """
    Магазин в кабинете продавца: всё публичное + служебное (реквизиты,
    настройки, статистика продаж...). Публичные поля наследуются, а не дублируются.
    """

    class Meta(ShopPublicSerializer.Meta):
        fields = [*ShopPublicSerializer.Meta.fields, "updated_at"]
        read_only_fields = ["id", "products_count", "created_at", "updated_at"]

    def create(self, validated_data):
        return services.create_shop(**validated_data)

    def update(self, instance, validated_data):
        return services.update_shop(instance, **validated_data)


class SellerProfileSerializer(UserSerializer):
    shops = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = [*UserSerializer.Meta.fields, "shops"]
        read_only_fields = fields

    def get_shops(self, user):
        return ShopBriefSerializer(Shop.objects.managed_by(user), many=True).data
