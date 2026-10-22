from django.contrib import admin

from . import services
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Сохранение и удаление — через reviews.services: они пересчитывают оценку товара."""

    list_display = ("product", "author", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("product__title", "author__email", "pros", "cons", "comment")
    raw_id_fields = ("product", "author")
    readonly_fields = ("created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        services.save_review(obj, previous_product_id=form.initial.get("product") if change else None)

    def delete_model(self, request, obj):
        services.delete_review(obj)

    def delete_queryset(self, request, queryset):
        services.delete_reviews(queryset)
