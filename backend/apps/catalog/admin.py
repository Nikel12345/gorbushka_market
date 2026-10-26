from django import forms
from django.contrib import admin
from django.forms.models import BaseInlineFormSet

from apps.core.exceptions import BusinessError
from apps.core.files import delete_file_on_commit

from . import accessories, services, variants
from .categories import check_parent
from .models import (
    Category,
    Characteristic,
    CharacteristicValue,
    Product,
    ProductAccessory,
    ProductCharacteristic,
    ProductGroup,
    ProductImage,
)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "position")


class ProductCharacteristicForm(forms.ModelForm):
    class Meta:
        model = ProductCharacteristic
        fields = ("value",)

    def clean(self):
        cleaned = super().clean()
        # Характеристика — та, к которой относится выбранное значение
        if cleaned.get("value"):
            self.instance.characteristic_id = cleaned["value"].characteristic_id
        return cleaned


class ProductCharacteristicFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        values = [
            form.cleaned_data["value"]
            for form in self.forms
            if form.cleaned_data.get("value") and not form.cleaned_data.get("DELETE")
        ]
        # self.instance — товар с уже применёнными полями формы (группа, статус), ещё не сохранённый
        try:
            variants.check_variant(self.instance, values)
        except BusinessError as error:
            raise forms.ValidationError(error.message) from error


class ProductCharacteristicInline(admin.TabularInline):
    model = ProductCharacteristic
    form = ProductCharacteristicForm
    formset = ProductCharacteristicFormSet
    extra = 0
    fields = ("value",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "value":
            # Список «Цвет: Синий» — сгруппирован по характеристикам
            kwargs["queryset"] = CharacteristicValue.objects.select_related("characteristic").order_by(
                "characteristic__sort_order", "characteristic_id", "sort_order", "id"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class AccessoryFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        chosen = [
            form.cleaned_data["accessory"]
            for form in self.forms
            if form.cleaned_data.get("accessory") and not form.cleaned_data.get("DELETE")
        ]
        # self.instance — группа или товар без группы (с уже применёнными полями формы)
        if isinstance(self.instance, ProductGroup):
            owner = {"group_id": self.instance.pk, "product_id": None}
        else:
            owner = {"group_id": self.instance.group_id, "product_id": self.instance.pk}
        try:
            accessories.check_accessories(chosen, **owner)
        except BusinessError as error:
            raise forms.ValidationError(error.message) from error


class AccessoryInline(admin.TabularInline):
    """Аксессуары модели (catalog/accessories.py). Снятые с продажи можно оставить — на витрине они скрыты."""

    model = ProductAccessory
    formset = AccessoryFormSet
    extra = 0
    fields = ("accessory", "position")
    autocomplete_fields = ("accessory",)


class ProductAccessoryInline(AccessoryInline):
    fk_name = "product"


class GroupAccessoryInline(AccessoryInline):
    fk_name = "group"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Фото редактируются блоком «Фото товара». Обложка — кеш первого фото,
    её пересчитывает services.sync_cover после сохранения.
    Характеристики и группа вариантов проверяются по правилам catalog/variants.py.
    Аксессуары товара группы вариантов — общие для группы, они на странице группы.
    """

    list_display = ("title", "category", "group", "price_usd", "price_rub", "quantity", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "category__name", "group__name")
    raw_id_fields = ("shop",)
    autocomplete_fields = ("category", "group")
    filter_horizontal = ("delivery_methods",)
    readonly_fields = ("image", "rating", "reviews_count", "created_at", "updated_at")
    inlines = [ProductCharacteristicInline, ProductImageInline, ProductAccessoryInline]

    def get_inlines(self, request, obj):
        if obj is not None and obj.group_id is not None:
            return [ProductCharacteristicInline, ProductImageInline]
        return self.inlines

    @admin.display(description="цена, ₽")
    def price_rub(self, obj):
        return obj.price

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
        if "group" in form.changed_data:
            services.keep_accessories_on_group_change(form.instance, old_group_id=form.initial.get("group"))


class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = "__all__"

    def clean_parent(self):
        parent = self.cleaned_data["parent"]
        try:
            check_parent(self.instance, parent)
        except BusinessError as error:
            raise forms.ValidationError(error.message) from error
        return parent


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Адрес (slug) можно не заполнять — сгенерируется из названия. Удалить можно только
    категорию без подкатегорий и товаров (в том числе снятых с продажи).
    """

    form = CategoryAdminForm
    list_display = ("name", "parent", "slug", "sort_order")
    list_filter = ("parent",)
    search_fields = ("name", "slug")
    autocomplete_fields = ("parent",)
    readonly_fields = ("created_at", "updated_at")


class CharacteristicValueInline(admin.TabularInline):
    model = CharacteristicValue
    extra = 0
    fields = ("value", "sort_order")


@admin.register(Characteristic)
class CharacteristicAdmin(admin.ModelAdmin):
    """
    Категория — где характеристика доступна (с подкатегориями), пусто — во всех.
    Значение, которое стоит у товаров, удалить нельзя — сначала замените его у товаров.
    """

    list_display = ("name", "category", "sort_order")
    search_fields = ("name", "category__name")
    autocomplete_fields = ("category",)
    inlines = [CharacteristicValueInline]


class ProductGroupAdminForm(forms.ModelForm):
    class Meta:
        model = ProductGroup
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        if "axes" in cleaned:
            self.instance.category = cleaned.get("category")
            try:
                variants.check_group(self.instance, list(cleaned["axes"]))
            except BusinessError as error:
                raise forms.ValidationError(error.message) from error
        return cleaned


class GroupProductInline(admin.TabularInline):
    """Товары группы — для обзора; группа и характеристики меняются на странице товара."""

    model = Product
    fields = ("title", "price_usd", "quantity", "status")
    readonly_fields = fields
    extra = 0
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    """
    Категория — где лежат товары группы (с подкатегориями); оси — из характеристик, доступных в ней.
    Аксессуары — общие для всех товаров группы.
    """

    form = ProductGroupAdminForm
    list_display = ("name", "category", "created_at")
    search_fields = ("name", "category__name")
    autocomplete_fields = ("category",)
    filter_horizontal = ("axes",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [GroupProductInline, GroupAccessoryInline]
