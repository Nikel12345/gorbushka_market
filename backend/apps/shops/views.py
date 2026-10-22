from rest_framework import generics
from rest_framework.permissions import AllowAny

from .mixins import ShopAdminMixin
from .models import Shop
from .serializers import ShopAdminSerializer, ShopPublicSerializer

# --- Админка магазина ---


class ShopAdminView(ShopAdminMixin, generics.RetrieveUpdateAPIView):
    """GET — магазин: публичные поля + служебные, PATCH — изменить."""

    serializer_class = ShopAdminSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return Shop.objects.with_stats().get(pk=self.get_shop().pk)


# --- Публичное ---


class ShopPublicDetailView(generics.RetrieveAPIView):
    """
    Страница магазина для покупателя (клик по магазину в карточке товара).
    Товары магазина — та же лента: GET /catalog/products/?shop=<id>
    """

    permission_classes = [AllowAny]
    serializer_class = ShopPublicSerializer
    lookup_url_kwarg = "shop_id"

    def get_queryset(self):
        return Shop.objects.public().with_stats()
