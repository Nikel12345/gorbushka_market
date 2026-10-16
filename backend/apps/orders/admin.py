from django import forms
from django.contrib import admin

from apps.core.exceptions import BusinessError

from . import statuses
from .models import Order, OrderItem, OrderStatusChange, Purchase, Shipment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "title", "price", "quantity")


class OrderStatusChangeInline(admin.TabularInline):
    """Журнал не редактируется: это история того, что уже произошло."""

    model = OrderStatusChange
    extra = 0
    fields = ("created_at", "from_status", "to_status", "actor", "user")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

    def clean_status(self):
        new_status = self.cleaned_data["status"]
        if self.instance.pk and new_status != self.instance.status:
            current = Order.objects.select_related("shipment__delivery_method").get(pk=self.instance.pk)
            try:
                statuses.check_forced_change(current, new_status)
            except BusinessError as error:
                raise forms.ValidationError(error.message) from error
        return new_status


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Всё редактируется. Смена статуса у существующего заказа идёт через
    orders.statuses.change_status (force): с возвратом остатков и денег при отмене,
    выручкой продавцу при выдаче и записью в журнал. Из финального статуса выйти нельзя.
    """

    form = OrderAdminForm
    list_display = ("id", "shop", "buyer", "status", "shipment", "total_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "shop__name", "buyer__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [OrderItemInline, OrderStatusChangeInline]

    def save_model(self, request, obj, form, change):
        if not change or "status" not in form.changed_data:
            super().save_model(request, obj, form, change)
            return

        new_status = obj.status
        obj.status = form.initial["status"]
        super().save_model(request, obj, form, change)  # остальные поля — как обычно
        try:
            statuses.change_status(obj, to=new_status, actor=OrderStatusChange.Actor.ADMIN, user=request.user, force=True)
        except BusinessError as error:
            self.message_user(request, f"Статус не изменён: {error.message}", level="error")
        obj.refresh_from_db()


class PurchaseOrderInline(admin.TabularInline):
    model = Order
    extra = 0
    fields = ("shop", "shipment", "status", "total_amount", "bonus_amount", "commission_amount")
    # Статус — на странице заказа: там его смена проходит через change_status
    readonly_fields = ("status",)
    show_change_link = True


class ShipmentInline(admin.TabularInline):
    model = Shipment
    extra = 0
    fields = ("delivery_method", "shop", "price", "bonus_amount", "address", "slot_date", "slot_start", "slot_end")


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "payment_method", "payment_status", "total_amount", "created_at")
    list_filter = ("payment_method", "payment_status")
    search_fields = ("id", "buyer__email")
    readonly_fields = ("created_at", "updated_at")
    inlines = [PurchaseOrderInline, ShipmentInline]
