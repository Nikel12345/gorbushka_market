from rest_framework import serializers

from apps.cart.serializers import CartLineSerializer
from apps.core.fields import ImageUrlField
from apps.delivery.serializers import DeliveryMethodBriefSerializer, DeliveryMethodSerializer
from apps.shops.serializers import ShopBriefSerializer
from apps.users.models import User

from . import statuses
from .checkout import DeliveryChoice, SlotChoice
from .models import Order, OrderItem, Purchase, Shipment


class OrderBuyerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


class ShipmentBriefSerializer(serializers.ModelSerializer):
    """Доставка заказа: способ и время. Это видят все стороны, в том числе продавец."""

    delivery_method = DeliveryMethodBriefSerializer(read_only=True)
    slot = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = ["id", "delivery_method", "slot"]
        read_only_fields = fields

    def get_slot(self, shipment) -> dict | None:
        if shipment.slot_date is None:
            return None
        return {
            "date": shipment.slot_date.isoformat(),
            "start": shipment.slot_start.strftime("%H:%M"),
            "end": shipment.slot_end.strftime("%H:%M"),
        }


class ShipmentSerializer(ShipmentBriefSerializer):
    """
    Отправка в покупке — для покупателя и курьера: + адрес, магазин (самовывоз),
    цена доставки, сколько из неё оплачено бонусами и сколько взять при вручении.
    """

    shop = ShopBriefSerializer(read_only=True, allow_null=True)
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta(ShipmentBriefSerializer.Meta):
        fields = [*ShipmentBriefSerializer.Meta.fields, "shop", "address", "price", "bonus_amount", "amount_due"]
        read_only_fields = fields


class OrderItemSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    # Устарело: доставка теперь у заказа (order.shipment), поле оставлено для совместимости
    shipment = ShipmentBriefSerializer(source="order.shipment", read_only=True, allow_null=True)
    # Текущее фото товара (не снимок): для узнаваемости в истории
    image = ImageUrlField(source="product.image", read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product_id", "title", "image", "price", "quantity", "total", "shipment"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    """
    Общая часть заказа для всех сторон. Наследники добавляют свои поля.
    available_statuses — куда текущий участник может перевести заказ (кнопки);
    участника задаёт view через контекст "order_actor".
    """

    # Название зависит от способа доставки: «Готов к выдаче» / «Передан курьеру», «Выдан» / «Доставлен»
    status_display = serializers.SerializerMethodField()
    available_statuses = serializers.SerializerMethodField()
    amount_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    # null — у заказов, оформленных до появления доставки
    shipment = ShipmentBriefSerializer(read_only=True, allow_null=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "status_display",
            "available_statuses",
            "total_amount",
            # из суммы заказа оплачено бонусами
            "bonus_amount",
            # сколько взять с покупателя при выдаче (только оплата при получении, иначе 0)
            "amount_due",
            "shipment",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_status_display(self, order) -> str:
        return statuses.status_label(order)

    def get_available_statuses(self, order) -> list[dict]:
        actor = self.context.get("order_actor")
        if actor is None:
            return []
        return [
            {"status": status, "name": statuses.label(order, status)}
            for status in statuses.available_statuses(order, actor)
        ]


class SellerOrderSerializer(OrderSerializer):
    """
    Продавцу важно, кто купил, оплачено ли (при самовывозе «при получении» деньги
    берёт он) и что покупатель написал в комментарии.
    """

    buyer = OrderBuyerSerializer(read_only=True)
    # null — у заказов, оформленных до появления покупок
    payment = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()
    # Выручка продавца = сумма заказа − комиссия маркета (бонусную часть доплачивает маркет)
    seller_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = [
            *OrderSerializer.Meta.fields,
            "buyer",
            "purchase_id",
            "payment",
            "comment",
            "commission_amount",
            "seller_amount",
        ]
        read_only_fields = fields

    def get_payment(self, order) -> dict | None:
        purchase = order.purchase
        if purchase is None:
            return None
        return {
            "method": purchase.payment_method,
            "method_display": purchase.get_payment_method_display(),
            "status": purchase.payment_status,
            "status_display": purchase.get_payment_status_display(),
        }

    def get_comment(self, order) -> str:
        return order.purchase.comment if order.purchase else ""


class MarketOrderSerializer(SellerOrderSerializer):
    """Маркету (курьеру) — ещё магазин, откуда забрать, и адрес доставки."""

    shop = ShopBriefSerializer(read_only=True)
    shipment = ShipmentSerializer(read_only=True, allow_null=True)

    class Meta(SellerOrderSerializer.Meta):
        fields = [*SellerOrderSerializer.Meta.fields, "shop"]
        read_only_fields = fields


class OrderStatusChangeRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)


class BuyerOrderSerializer(OrderSerializer):
    """Покупателю важно, где купил."""

    shop = ShopBriefSerializer(read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = [*OrderSerializer.Meta.fields, "shop", "purchase_id"]
        read_only_fields = fields


class PurchaseSerializer(serializers.ModelSerializer):
    """Покупка целиком: заказы магазинов с позициями и отправки."""

    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    orders = BuyerOrderSerializer(many=True, read_only=True)
    shipments = ShipmentSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id",
            "payment_method",
            "payment_method_display",
            "payment_status",
            "payment_status_display",
            "items_total",
            "delivery_total",
            "total_amount",
            "bonus_amount",
            "comment",
            "orders",
            "shipments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# --- Оформление ---


class CheckoutProblemSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True)


class CheckoutItemSerializer(CartLineSerializer):
    """Позиция, которую можно оформить, и способы доставки на выбор."""

    delivery_methods = DeliveryMethodSerializer(many=True, read_only=True)
    pickup_address = serializers.CharField(read_only=True, allow_null=True)


class CheckoutUnavailableItemSerializer(CartLineSerializer):
    """Позиция, которая не будет оформлена (останется в корзине), и почему."""

    problem = CheckoutProblemSerializer(read_only=True)


class PaymentMethodSerializer(serializers.Serializer):
    code = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


class CheckoutPreviewSerializer(serializers.Serializer):
    items = CheckoutItemSerializer(many=True, read_only=True)
    unavailable_items = CheckoutUnavailableItemSerializer(many=True, read_only=True)
    items_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    payment_methods = PaymentMethodSerializer(many=True, read_only=True)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    # Для переключателя «оплатить бонусами»: сколько есть и какую часть итога можно ими покрыть
    bonus = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    bonus_max_share = serializers.DecimalField(max_digits=4, decimal_places=2, read_only=True)
    can_checkout = serializers.BooleanField(read_only=True)


class PlannedShipmentSerializer(serializers.Serializer):
    delivery_method = DeliveryMethodBriefSerializer(source="method", read_only=True)
    shop = ShopBriefSerializer(read_only=True, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_ids = serializers.ListField(child=serializers.IntegerField(), read_only=True)


class CheckoutPlanSerializer(serializers.Serializer):
    shipments = PlannedShipmentSerializer(many=True, read_only=True)
    items_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    delivery_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    bonus_amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    # итог минус бонусы: спишется с баланса или будет оплачено при получении
    amount_to_pay = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)


class DeliveryChoiceSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    delivery_method_id = serializers.IntegerField(min_value=1)


class SlotChoiceSerializer(serializers.Serializer):
    delivery_method_id = serializers.IntegerField(min_value=1)
    date = serializers.DateField()
    window_id = serializers.IntegerField(min_value=1)


class CheckoutQuoteRequestSerializer(serializers.Serializer):
    """Способ доставки для каждой позиции, которую можно оформить."""

    items = DeliveryChoiceSerializer(many=True, allow_empty=False)
    # Переключатель «оплатить бонусами»: спишутся все, но не больше BONUS_MAX_SHARE итога
    use_bonus = serializers.BooleanField(default=False)

    def service_kwargs(self) -> dict:
        return {
            "choices": [DeliveryChoice(**item) for item in self.validated_data["items"]],
            "use_bonus": self.validated_data["use_bonus"],
        }


class CheckoutRequestSerializer(CheckoutQuoteRequestSerializer):
    # Время — одно на способ доставки с выбором времени
    slots = SlotChoiceSerializer(many=True, required=False)
    # Адрес доставки — обязателен, если выбран способ с requires_address
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=Purchase.PaymentMethod.choices)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    # Итог, который видел покупатель: если не совпал с пересчитанным — 409
    expected_total = serializers.DecimalField(max_digits=12, decimal_places=2)

    def service_kwargs(self) -> dict:
        data = self.validated_data
        return {
            **super().service_kwargs(),
            "slots": [SlotChoice(**slot) for slot in data.get("slots", [])],
            "address": data.get("address", ""),
            "payment_method": data["payment_method"],
            "comment": data.get("comment", ""),
            "expected_total": data["expected_total"],
        }
