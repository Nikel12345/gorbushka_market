from rest_framework.permissions import IsAdminUser

from apps.core.exceptions import BusinessNotFound

from .models import Shop


class ShopAdminMixin:
    """
    Для view админки магазина (/admin/...). Доступ — только сотрудники (is_staff),
    остальным 403. Магазин один: get_shop() отдаёт его, пока не заведён — 404.
    """

    permission_classes = [IsAdminUser]

    def get_shop(self) -> Shop:
        if not hasattr(self, "_shop"):
            self._shop = Shop.objects.current()
            if self._shop is None:
                raise BusinessNotFound("Магазин ещё не заведён — создайте его в админке.", code="shop_not_found")
        return self._shop

    def get_serializer_context(self):
        # Сериализаторам нужен магазин (например, для проверки доступных ему способов доставки)
        return {**super().get_serializer_context(), "shop": self.get_shop()}
