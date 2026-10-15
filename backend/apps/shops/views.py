from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Shop
from .serializers import SellerProfileSerializer, SellerShopSerializer, ShopPublicSerializer

# --- Кабинет продавца ---


class SellerProfileView(APIView):
    """Профиль продавца: данные пользователя + магазины, которыми он управляет."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(SellerProfileSerializer(request.user).data)


class SellerShopListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerShopSerializer
    pagination_class = None  # магазинов у продавца единицы

    def get_queryset(self):
        return Shop.objects.managed_by(self.request.user).with_stats()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class SellerShopDetailView(generics.RetrieveUpdateAPIView):
    """GET — расширенная информация о магазине, PATCH — изменить."""

    permission_classes = [IsAuthenticated]
    serializer_class = SellerShopSerializer
    lookup_url_kwarg = "shop_id"
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Shop.objects.managed_by(self.request.user).with_stats()


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
