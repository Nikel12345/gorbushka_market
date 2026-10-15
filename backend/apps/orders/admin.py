from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "title", "price", "quantity")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Заказы создаются только через orders.services.create_order (цены, остатки,
    сумма считаются там). В админке — просмотр и смена статуса.
    """

    list_display = ("id", "shop", "buyer", "status", "total_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("id", "shop__name", "buyer__email")
    readonly_fields = ("shop", "buyer", "total_amount", "created_at", "updated_at")
    inlines = [OrderItemInline]

    def has_add_permission(self, request):
        return False
