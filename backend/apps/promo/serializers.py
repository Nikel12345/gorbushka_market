from rest_framework import serializers

from apps.core.fields import ImageUrlField
from apps.shops.serializers import ShopBriefSerializer

from .models import Promo


class PromoSerializer(serializers.ModelSerializer):
    image = ImageUrlField(read_only=True)
    image_mobile = ImageUrlField(read_only=True)
    shop = ShopBriefSerializer(read_only=True)

    class Meta:
        model = Promo
        fields = ["id", "title", "image", "image_mobile", "shop", "filters", "url"]
        read_only_fields = fields
