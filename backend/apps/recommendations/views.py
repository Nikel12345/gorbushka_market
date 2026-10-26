from django.http import Http404
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.cart.services import get_request_cart
from apps.catalog.models import Product
from apps.catalog.serializers import ProductCardSerializer

from .cart import cart_recommendations
from .pagination import CartRecommendationsPagination


class BoughtTogetherView(generics.ListAPIView):
    """
    «С этим товаром часто покупают»: карточки товаров на продаже (до services.TOP_SIZE),
    сначала самые частые. Пусто — данных пока нет. Снятый с продажи товар — 404.
    """

    permission_classes = [AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = None

    def get_queryset(self):
        product_id = self.kwargs["product_id"]
        if not Product.objects.on_sale().filter(pk=product_id).exists():
            raise Http404
        return (
            Product.objects.on_sale()
            .filter(bought_with__product_id=product_id)
            .select_related("shop")
            .order_by("bought_with__position")
        )


class CartRecommendationsView(generics.GenericAPIView):
    """
    «Рекомендуем» в корзине (покупателя или гостя): сначала аксессуары товаров корзины, потом лента
    главной. Порции по курсору, как в ленте: {next_cursor, results}. См. recommendations/cart.py.
    """

    permission_classes = [AllowAny]
    serializer_class = ProductCardSerializer
    pagination_class = CartRecommendationsPagination

    def get(self, request):
        products = self.paginator.paginate_recommendations(cart_recommendations(get_request_cart(request)), request)
        return self.get_paginated_response(self.get_serializer(products, many=True).data)
