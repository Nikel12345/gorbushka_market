from django.contrib import admin

from apps.core.files import delete_file_on_commit

from . import services
from .models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "position")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Фото редактируются блоком «Фото товара». Обложка — кеш первого фото,
    её пересчитывает services.sync_cover после сохранения.
    """

    list_display = ("title", "shop", "price", "quantity", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "shop__name")
    raw_id_fields = ("shop",)
    filter_horizontal = ("delivery_methods",)
    readonly_fields = ("image", "created_at", "updated_at")
    inlines = [ProductImageInline]

    def save_formset(self, request, form, formset, change):
        if formset.model is ProductImage:
            # Заменённый файл удаляем после коммита; удалённые записи чистит catalog/signals.py
            for image_form in formset.forms:
                if image_form in formset.deleted_forms:
                    continue
                if image_form.instance.pk and "image" in image_form.changed_data:
                    delete_file_on_commit(image_form.initial.get("image"))
        super().save_formset(request, form, formset, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        services.sync_cover(form.instance)
