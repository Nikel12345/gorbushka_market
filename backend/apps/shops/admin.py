from django.contrib import admin

from .models import Shop


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Магазин один: завести можно, только пока его нет; удалить нельзя (на него ссылаются товары и заказы)."""

    list_display = ("name", "address", "created_at")
    search_fields = ("name", "address")

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not Shop.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
