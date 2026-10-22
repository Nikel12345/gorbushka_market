from django.http import Http404
from rest_framework import generics
from rest_framework.permissions import AllowAny

from apps.catalog.models import Product
from apps.catalog.serializers import ProductCardSerializer


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
