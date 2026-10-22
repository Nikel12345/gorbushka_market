from django.contrib import admin
from django.utils.html import format_html

from apps.core.files import delete_file_on_commit

from .models import Promo


@admin.register(Promo)
class PromoAdmin(admin.ModelAdmin):
    list_display = ("title", "preview", "placement", "url", "position", "is_active", "starts_at", "ends_at")
    list_display_links = ("title", "preview")
    list_editable = ("position", "is_active")
    list_filter = ("placement", "is_active")
    search_fields = ("title", "url")
    readonly_fields = ("preview", "created_at", "updated_at")

    @admin.display(description="картинка")
    def preview(self, obj):
        if not obj.image:
            return "—"
        return format_html('<img src="{}" style="max-height:48px;max-width:240px">', obj.image.url)

    def save_model(self, request, obj, form, change):
        # Заменённые или убранные картинки удаляем из хранилища после коммита
        if change:
            for field in ("image", "image_mobile"):
                if field in form.changed_data:
                    delete_file_on_commit(form.initial.get(field))
        super().save_model(request, obj, form, change)
