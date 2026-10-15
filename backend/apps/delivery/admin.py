from django.contrib import admin

from .models import DeliveryMethod, DeliveryTimeWindow


class DeliveryTimeWindowInline(admin.TabularInline):
    model = DeliveryTimeWindow
    extra = 0


@admin.register(DeliveryMethod)
class DeliveryMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "kind", "provider", "price", "is_active", "sort_order")
    list_filter = ("kind", "provider", "is_active")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name", "code")
    inlines = [DeliveryTimeWindowInline]
