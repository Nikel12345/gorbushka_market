from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import DeliveryMethod, DeliveryTimeWindow
from .serializers import DeliveryMethodSerializer, DeliverySlotSerializer


class DeliveryMethodListView(generics.ListAPIView):
    """Активные способы доставки: форма товара у продавца, фильтр ленты, справка."""

    permission_classes = [AllowAny]
    serializer_class = DeliveryMethodSerializer
    pagination_class = None

    def get_queryset(self):
        return DeliveryMethod.objects.active()


class DeliveryMethodSlotsView(APIView):
    """Доступные дата+интервал для способа. Для способов без выбора времени — []."""

    permission_classes = [AllowAny]

    def get(self, request, method_id):
        method = get_object_or_404(
            DeliveryMethod.objects.active().prefetch_related(
                Prefetch("time_windows", queryset=DeliveryTimeWindow.objects.filter(is_active=True))
            ),
            pk=method_id,
        )
        return Response(DeliverySlotSerializer(services.get_slots(method), many=True).data)
