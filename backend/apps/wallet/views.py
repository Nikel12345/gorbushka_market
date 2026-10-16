from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import BalanceSerializer


class BalanceView(APIView):
    """Части баланса: доступно для вывода, бонусы, заморожено и «для покупок» (доступно + бонусы)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(BalanceSerializer(services.get_wallet(request.user)).data)
