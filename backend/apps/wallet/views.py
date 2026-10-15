from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import BalanceSerializer


class BalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(BalanceSerializer({"balance": services.get_balance(request.user)}).data)
