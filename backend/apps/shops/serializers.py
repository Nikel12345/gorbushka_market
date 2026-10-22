from rest_framework import serializers

from . import services
from .models import Shop


class ShopBriefSerializer(serializers.ModelSerializer):
    """Магазин в чужих ответах: карточка товара, заказ."""

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


class ShopAdminSerializer(ShopPublicSerializer):
    """
    Магазин в админке: всё публичное + служебное (реквизиты,
    настройки, статистика продаж...). Публичные поля наследуются, а не дублируются.
    """

    class Meta(ShopPublicSerializer.Meta):
        fields = [*ShopPublicSerializer.Meta.fields, "updated_at"]
        read_only_fields = ["id", "products_count", "created_at", "updated_at"]

    def validate_address(self, address):
        # Нельзя стереть адрес, пока у товаров магазина есть самовывоз: покупателю некуда идти
        if not address and self.instance is not None and self.instance.address:
            from apps.catalog.models import Product
            from apps.delivery.models import DeliveryMethod

            uses_pickup = (
                Product.objects.filter(shop=self.instance)
                .on_sale()
                .filter(delivery_methods__in=DeliveryMethod.objects.needing_shop_address())
                .exists()
            )
            if uses_pickup:
                raise serializers.ValidationError(
                    "Нельзя убрать адрес: у товаров магазина выбран самовывоз.",
                    code="shop_address_in_use",
                )
        return address

    def update(self, instance, validated_data):
        return services.update_shop(instance, **validated_data)
