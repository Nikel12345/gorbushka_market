from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "shop", "price", "quantity", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "shop__name")
    raw_id_fields = ("shop",)
    filter_horizontal = ("delivery_methods",)
