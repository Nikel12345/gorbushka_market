from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import CartAddSerializer, CartQuantitySerializer, CartSerializer


class CartResponseMixin:
    """Любое действие с корзиной возвращает её актуальное содержимое целиком. Корзина есть и у гостя."""

    permission_classes = [AllowAny]

    # DRF проверяет CSRF только у вошедших — для гостя (корзина по сессии) включаем явно
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def cart_response(self, status_code=status.HTTP_200_OK):
        cart = services.get_request_cart(self.request)
        return Response(CartSerializer(services.get_cart(cart)).data, status=status_code)


class CartView(CartResponseMixin, APIView):
    """GET — содержимое корзины, DELETE — очистить."""

    def get(self, request):
        return self.cart_response()

    def delete(self, request):
        services.clear_cart(services.get_request_cart(request))
        return self.cart_response()


class CartItemListView(CartResponseMixin, APIView):
    """POST {product_id, quantity=1} — положить товар (если уже есть — прибавить)."""

    def post(self, request):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.add_item(services.get_request_cart(request, create=True), **serializer.validated_data)
        return self.cart_response(status.HTTP_201_CREATED)


class CartItemDetailView(CartResponseMixin, APIView):
    """PATCH {quantity} — задать количество (0 — убрать), DELETE — убрать товар."""

    def patch(self, request, product_id):
        serializer = CartQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_item_quantity(
            services.get_request_cart(request), product_id=product_id, **serializer.validated_data
        )
        return self.cart_response()

    def delete(self, request, product_id):
        services.remove_item(services.get_request_cart(request), product_id=product_id)
        return self.cart_response()
