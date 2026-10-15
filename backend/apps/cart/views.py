from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import CartAddSerializer, CartQuantitySerializer, CartSerializer


class CartResponseMixin:
    """Любое действие с корзиной возвращает её актуальное содержимое целиком."""

    permission_classes = [IsAuthenticated]

    def cart_response(self, status_code=status.HTTP_200_OK):
        return Response(CartSerializer(services.get_cart(self.request.user)).data, status=status_code)


class CartView(CartResponseMixin, APIView):
    """GET — содержимое корзины, DELETE — очистить."""

    def get(self, request):
        return self.cart_response()

    def delete(self, request):
        services.clear_cart(request.user)
        return self.cart_response()


class CartItemListView(CartResponseMixin, APIView):
    """POST {product_id, quantity=1} — положить товар (если уже есть — прибавить)."""

    def post(self, request):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.add_item(request.user, **serializer.validated_data)
        return self.cart_response(status.HTTP_201_CREATED)


class CartItemDetailView(CartResponseMixin, APIView):
    """PATCH {quantity} — задать количество (0 — убрать), DELETE — убрать товар."""

    def patch(self, request, product_id):
        serializer = CartQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_item_quantity(request.user, product_id=product_id, **serializer.validated_data)
        return self.cart_response()

    def delete(self, request, product_id):
        services.remove_item(request.user, product_id=product_id)
        return self.cart_response()
