from rest_framework import serializers

from .models import DeliveryMethod


class DeliveryMethodBriefSerializer(serializers.ModelSerializer):
    """Способ доставки в чужих ответах (например, выбранный в заказе)."""

    class Meta:
        model = DeliveryMethod
        fields = ["id", "code", "name", "kind", "provider"]
        read_only_fields = fields


class DeliveryMethodSerializer(DeliveryMethodBriefSerializer):
    """Способ доставки со всеми условиями: справочник, товар, варианты при оформлении."""

    eta = serializers.SerializerMethodField()
    has_slots = serializers.BooleanField(read_only=True)

    class Meta(DeliveryMethodBriefSerializer.Meta):
        fields = [
            *DeliveryMethodBriefSerializer.Meta.fields,
            "description",
            "price",
            "eta",
            "requires_address",
            "has_slots",
        ]
        read_only_fields = fields

    def get_eta(self, method) -> dict | None:
        if method.eta_min_days is None:
            return None
        return {"min_days": method.eta_min_days, "max_days": method.eta_max_days}


class DeliverySlotSerializer(serializers.Serializer):
    date = serializers.DateField(read_only=True)
    window_id = serializers.IntegerField(read_only=True)
    start = serializers.TimeField(format="%H:%M", read_only=True)
    end = serializers.TimeField(format="%H:%M", read_only=True)
