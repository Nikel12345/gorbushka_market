from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ("product", "quantity", "created_at", "updated_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Только просмотр — корзиной управляет сам пользователь через API."""

    list_display = ("user", "updated_at")
    search_fields = ("user__email",)
    readonly_fields = ("user", "created_at", "updated_at")
    inlines = [CartItemInline]

    def has_add_permission(self, request):
        return False
