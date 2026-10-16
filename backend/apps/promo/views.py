import random

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Promo
from .serializers import PromoSerializer


class FeedPromoView(APIView):
    """
    Случайная реклама для ленты на главной. Где и когда её показать, решает фронт.
    Нет ни одной — 204.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        promos = Promo.objects.live().filter(placement=Promo.Placement.FEED)
        # count + случайное смещение вместо order_by("?"): тот не использует индекс
        count = promos.count()
        if not count:
            return Response(status=status.HTTP_204_NO_CONTENT)
        promo = promos.select_related("shop")[random.randrange(count)]
        return Response(PromoSerializer(promo, context={"request": request}).data)
