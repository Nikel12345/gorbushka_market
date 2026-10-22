from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import usd_rate


class UsdRateView(APIView):
    """Текущий курс доллара: по нему цены товаров переводятся в рубли."""

    permission_classes = [AllowAny]

    def get(self, request):
        rate = usd_rate()
        return Response({"rate": str(rate.value), "date": rate.date})
