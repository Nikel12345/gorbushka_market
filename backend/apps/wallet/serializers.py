from rest_framework import serializers


class BalanceSerializer(serializers.Serializer):
    # Совместимость: раньше было единственное поле — реальные деньги (= available)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    available = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    bonus = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    spendable = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
