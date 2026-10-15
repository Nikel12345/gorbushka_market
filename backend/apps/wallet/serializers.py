from rest_framework import serializers


class BalanceSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
