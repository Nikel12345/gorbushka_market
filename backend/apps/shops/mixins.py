from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from .models import Shop


class SellerShopMixin:
    """
    Для view кабинета продавца, вложенных в /seller/shops/<shop_id>/...
    Чужой или несуществующий магазин — 404, чтобы не раскрывать, что он есть.
    """

    permission_classes = [IsAuthenticated]
    shop_url_kwarg = "shop_id"

    def get_shop(self) -> Shop:
        if not hasattr(self, "_shop"):
            self._shop = get_object_or_404(
                Shop.objects.managed_by(self.request.user),
                pk=self.kwargs[self.shop_url_kwarg],
            )
        return self._shop

    def get_serializer_context(self):
        # Сериализаторам вложенных view нужен магазин (например, для проверки доступных ему способов доставки)
        return {**super().get_serializer_context(), "shop": self.get_shop()}
