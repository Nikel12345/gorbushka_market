import base64
import binascii
import json

from rest_framework.exceptions import ValidationError

from apps.catalog.models import Product
from apps.catalog.pagination import ProductFeedPagination

from .cart import CartRecommendations


class CartRecommendationsPagination(ProductFeedPagination):
    """
    «Рекомендуем» в корзине одной лентой: сначала leading (аксессуары), потом rest — лента главной
    с сортировкой «новые». Порция на стыке добирается из ленты, а не обрывается.
    Курсор, пока идут аксессуары, — сколько их уже отдали; дальше — обычный курсор ленты.
    """

    def paginate_recommendations(self, recommendations: CartRecommendations, request) -> list[Product]:
        page_size = self._get_page_size(request)
        cursor = request.query_params.get(self.cursor_query_param)
        offset = self._decode_offset(cursor) if cursor else 0
        if offset is None:
            return self.paginate_keyset(recommendations.rest, sort_name=self.default_sort, cursor=cursor, page_size=page_size)

        ids = recommendations.leading[offset : offset + page_size]
        found = Product.objects.on_sale().select_related("shop").in_bulk(ids)
        items = [found[pk] for pk in ids if pk in found]
        if len(ids) == page_size:
            # Порция — одни аксессуары; если они на ней и кончились, лента начнётся со следующей
            self.next_cursor = self._encode_offset(offset + page_size)
            return items
        # Аксессуары кончились — остаток порции из начала ленты, дальше — её курсор
        return items + self.paginate_keyset(
            recommendations.rest, sort_name=self.default_sort, cursor=None, page_size=page_size - len(ids)
        )

    def _encode_offset(self, offset: int) -> str:
        payload = json.dumps({"lead": offset}, separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    def _decode_offset(self, raw: str) -> int | None:
        """Сколько аксессуаров уже отдали; None — это курсор ленты (его проверит paginate_keyset)."""
        try:
            payload = json.loads(base64.urlsafe_b64decode((raw + "=" * (-len(raw) % 4)).encode()).decode())
        except (ValueError, binascii.Error, UnicodeDecodeError):
            raise ValidationError({self.cursor_query_param: [self.invalid_cursor_message]})
        if not isinstance(payload, dict) or "lead" not in payload:
            return None
        offset = payload["lead"]
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValidationError({self.cursor_query_param: [self.invalid_cursor_message]})
        return offset
