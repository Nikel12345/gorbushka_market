from django.conf import settings
from django.db.models import Q
from rest_framework import serializers

from apps.core.fields import ImageUrlField
from apps.core.validators import MaxFileSizeValidator
from apps.delivery.models import DeliveryMethod
from apps.delivery.serializers import DeliveryMethodSerializer
from apps.shops.serializers import ShopBriefSerializer

from . import services, variants
from .categories import CategoryTree
from .models import (
    Category,
    Characteristic,
    CharacteristicValue,
    Product,
    ProductCharacteristic,
    ProductGroup,
    ProductImage,
)
from .search import normalize


def category_tree(context: dict) -> CategoryTree:
    """Дерево категорий — одно на весь ответ (кладётся в контекст сериализатора при первом обращении)."""
    if "category_tree" not in context:
        context["category_tree"] = CategoryTree.load()
    return context["category_tree"]


def _check_new_name(existing, name: str, message: str) -> str:
    """«Чёрный», «черный» и «ЧЁРНЫЙ» — одно значение: иначе в вариантах будут две кнопки."""
    if normalize(name) in {normalize(item) for item in existing}:
        raise serializers.ValidationError(message, code="unique")
    return name


class CategorySerializer(serializers.ModelSerializer):
    """
    Категория в плоском списке дерева (родитель, затем его подкатегории): depth — уровень
    (корень — 0), products_count — товары на продаже вместе с подкатегориями.
    """

    # Запись: перенос под другую категорию, null — в корень
    parent_id = serializers.PrimaryKeyRelatedField(
        source="parent",
        required=False,
        allow_null=True,
        queryset=Category.objects.all(),
    )
    depth = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent_id", "sort_order", "depth", "products_count"]

    def get_depth(self, category) -> int:
        return len(category_tree(self.context).path(category.id)) - 1

    def get_products_count(self, category) -> int:
        if "products_count" not in self.context:
            self.context["products_count"] = category_tree(self.context).products_count()
        return self.context["products_count"].get(category.id, 0)

    def validate(self, attrs):
        # Одинаковые названия у соседей путают и в меню, и в форме товара
        name = attrs.get("name", getattr(self.instance, "name", ""))
        parent = attrs["parent"] if "parent" in attrs else getattr(self.instance, "parent", None)
        siblings = Category.objects.filter(parent=parent).exclude(pk=getattr(self.instance, "pk", None))
        place = f"в «{parent}»" if parent else "на верхнем уровне"
        try:
            _check_new_name(siblings.values_list("name", flat=True), name, f"Категория «{name}» уже есть {place}.")
        except serializers.ValidationError as error:
            raise serializers.ValidationError({"name": error.detail}) from error
        return attrs

    def create(self, validated_data):
        return services.create_category(**validated_data)

    def update(self, instance, validated_data):
        return services.update_category(instance, **validated_data)


class CategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class CharacteristicValueSerializer(serializers.ModelSerializer):
    """Значение из справочника. Создаётся в своей характеристике: characteristic — из контекста view."""

    class Meta:
        model = CharacteristicValue
        fields = ["id", "value", "sort_order"]

    def validate_value(self, value):
        characteristic = self.context["characteristic"]
        return _check_new_name(
            characteristic.values.values_list("value", flat=True),
            value,
            f"У характеристики «{characteristic}» уже есть значение «{value}».",
        )


class CharacteristicSerializer(serializers.ModelSerializer):
    """
    Характеристика со справочником значений. category — где доступна (с подкатегориями),
    null — во всех категориях.
    """

    category = CategoryBriefSerializer(read_only=True)
    # Запись: id категории, null — во всех категориях
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
        queryset=Category.objects.all(),
    )
    values = CharacteristicValueSerializer(many=True, read_only=True)

    class Meta:
        model = Characteristic
        fields = ["id", "name", "category", "category_id", "sort_order", "values"]

    def validate(self, attrs):
        # Два «Цвета», видимых одному товару, путали бы форму: название уникально в ветке —
        # среди общих, категорий выше, самой категории и её подкатегорий
        name = attrs.get("name", getattr(self.instance, "name", ""))
        category = attrs["category"] if "category" in attrs else getattr(self.instance, "category", None)
        others = Characteristic.objects.exclude(pk=getattr(self.instance, "pk", None))
        if category is not None:
            branch = category_tree(self.context).branch_ids(category.id)
            others = others.filter(Q(category__isnull=True) | Q(category_id__in=branch))
        try:
            _check_new_name(others.values_list("name", flat=True), name, f"Характеристика «{name}» в этой ветке уже есть.")
        except serializers.ValidationError as error:
            raise serializers.ValidationError({"name": error.detail}) from error
        return attrs

    def update(self, instance, validated_data):
        return services.update_characteristic(instance, **validated_data)


class CharacteristicBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Characteristic
        fields = ["id", "name"]


class ProductGroupSerializer(serializers.ModelSerializer):
    """
    Группа вариантов. category — где лежат её товары (с подкатегориями), null — где угодно.
    axes — характеристики, по которым различаются её товары.
    """

    category = CategoryBriefSerializer(read_only=True)
    # Запись: id категории, null — без категории (оси — только общие характеристики)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
        queryset=Category.objects.all(),
    )
    axes = CharacteristicBriefSerializer(many=True, read_only=True)
    # Запись: список id характеристик. В PATCH, если передан, заменяет набор целиком
    axis_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        allow_empty=False,
        queryset=Characteristic.objects.all(),
    )

    class Meta:
        model = ProductGroup
        fields = ["id", "name", "category", "category_id", "axes", "axis_ids"]

    def _to_service_kwargs(self, validated_data):
        if "axis_ids" in validated_data:
            validated_data["axes"] = list(dict.fromkeys(validated_data.pop("axis_ids")))
        return validated_data

    def create(self, validated_data):
        return services.create_group(**self._to_service_kwargs(validated_data))

    def update(self, instance, validated_data):
        return services.update_group(instance, **self._to_service_kwargs(validated_data))


class ProductGroupBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGroup
        fields = ["id", "name"]


class ProductCharacteristicSerializer(serializers.ModelSerializer):
    """
    Характеристика товара: «Цвет: Синий». in_category=false — характеристика недоступна
    в категории товара (их перенесли): на витрине её не видно, в админке её нужно поправить.
    """

    characteristic_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source="characteristic.name", read_only=True)
    value_id = serializers.IntegerField(read_only=True)
    value = serializers.CharField(source="value.value", read_only=True)
    in_category = serializers.SerializerMethodField()

    class Meta:
        model = ProductCharacteristic
        fields = ["characteristic_id", "name", "value_id", "value", "in_category"]

    def get_in_category(self, row) -> bool:
        if row.characteristic.category_id is None:
            return True
        return category_tree(self.context).allows(row.characteristic, row.product.category_id)


def product_image_field(**kwargs):
    """Загрузка одного фото товара: проверка, что это картинка, и лимит размера."""
    return ImageUrlField(validators=[MaxFileSizeValidator(setting="PRODUCT_IMAGE_MAX_BYTES")], **kwargs)


class ProductImageSerializer(serializers.ModelSerializer):
    """Фото товара. Чтение — {id, url}; загрузка — файл в поле image (multipart)."""

    url = ImageUrlField(source="image", read_only=True)
    image = product_image_field(write_only=True, required=True, allow_null=False)

    class Meta:
        model = ProductImage
        fields = ["id", "url", "image"]

    def create(self, validated_data):
        # product приходит из view через serializer.save(product=...)
        return services.add_images(validated_data["product"], [validated_data["image"]])[0]


class ProductImagesField(serializers.ListField):
    """
    Фото товара в его сериализаторе. Чтение — все фото по порядку [{id, url}], первое — обложка.
    Запись — файлы (повторяющееся поле в multipart), они добавляются в конец.
    """

    child = product_image_field(allow_null=False)

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_representation(self, images):
        return ProductImageSerializer(images.all(), many=True, context=self.context).data


class ProductAdminSerializer(serializers.ModelSerializer):
    """Товар в админке магазина. Цену задают в долларах (price_usd), price — она же в рублях по текущему курсу."""

    price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    # Обложка (первое фото). Запись — старый способ с одной картинкой: файл заменяет
    # обложку, null убирает её. Новый способ — images и /images/.
    image = product_image_field()
    images = ProductImagesField()
    category = CategoryBriefSerializer(read_only=True)
    # Запись: id категории, null — убрать из категории
    category_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=False,
        allow_null=True,
        queryset=Category.objects.all(),
    )
    delivery_methods = DeliveryMethodSerializer(many=True, read_only=True)
    # Запись: список id способов (JSON-массив или повторяющееся поле в multipart).
    # Обязателен при создании; в PATCH, если передан, заменяет набор целиком.
    delivery_method_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        allow_empty=False,
        queryset=DeliveryMethod.objects.all(),
    )
    group = ProductGroupBriefSerializer(read_only=True)
    # Запись: id группы вариантов, null — убрать из группы
    group_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=False,
        allow_null=True,
        queryset=ProductGroup.objects.all(),
    )
    characteristics = ProductCharacteristicSerializer(many=True, read_only=True)
    # Запись: id значений из справочника, по одному на характеристику. В PATCH, если передан,
    # заменяет набор целиком. Товару в группе нужны значения всех её осей (catalog/variants.py)
    characteristic_value_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        queryset=CharacteristicValue.objects.select_related("characteristic"),
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_id",
            "price_usd",
            "price",
            "quantity",
            "image",
            "images",
            "delivery_methods",
            "delivery_method_ids",
            "group",
            "group_id",
            "characteristics",
            "characteristic_value_ids",
            "status",
            "status_display",
            "rating",
            "reviews_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "status_display", "rating", "reviews_count", "created_at", "updated_at"]

    def validate_delivery_method_ids(self, methods):
        # shop кладёт в контекст ShopAdminMixin
        shop = self.context["shop"]
        allowed = set(DeliveryMethod.objects.available_for_shop(shop).values_list("pk", flat=True))
        unavailable = [method.name for method in methods if method.pk not in allowed]
        if unavailable:
            raise serializers.ValidationError(f"Способы доставки недоступны: {', '.join(unavailable)}.")
        if not shop.address:
            need_address = [method.name for method in methods if method.needs_shop_address]
            if need_address:
                raise serializers.ValidationError(
                    f"Укажите адрес магазина, чтобы выбрать: {', '.join(need_address)}.",
                    code="shop_address_required",
                )
        return list(dict.fromkeys(methods))

    def validate_images(self, files):
        # Предварительная проверка для понятной ошибки поля; точная — в сервисе под блокировкой
        limit = settings.PRODUCT_IMAGES_MAX
        existing = self.instance.images.count() if self.instance else 0
        if existing + len(files) > limit:
            raise serializers.ValidationError(f"У товара может быть не больше {limit} фото.", code="too_many_images")
        return files

    def _to_service_kwargs(self, validated_data):
        if "delivery_method_ids" in validated_data:
            validated_data["delivery_methods"] = validated_data.pop("delivery_method_ids")
        if "category_id" in validated_data:
            validated_data["category"] = validated_data.pop("category_id")
        if "group_id" in validated_data:
            validated_data["group"] = validated_data.pop("group_id")
        if "characteristic_value_ids" in validated_data:
            validated_data["characteristic_values"] = list(dict.fromkeys(validated_data.pop("characteristic_value_ids")))
        return validated_data

    def create(self, validated_data):
        # shop приходит из view через serializer.save(shop=...)
        return services.create_product(**self._to_service_kwargs(validated_data))

    def update(self, instance, validated_data):
        return services.update_product(instance, **self._to_service_kwargs(validated_data))


class ProductCardSerializer(serializers.ModelSerializer):
    """Карточка товара в публичной ленте — без тяжёлых полей."""

    shop = ShopBriefSerializer(read_only=True)
    # В рублях по текущему курсу (в базе цена в долларах)
    price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    in_stock = serializers.SerializerMethodField()
    image = ImageUrlField(read_only=True)

    class Meta:
        model = Product
        # rating — средняя оценка по отзывам ("4.75"; "0.00" — отзывов нет), см. apps/reviews
        fields = ["id", "title", "price", "image", "in_stock", "shop", "rating", "reviews_count", "created_at"]
        read_only_fields = fields

    def get_in_stock(self, product) -> bool:
        return product.quantity > 0


class AccessoryCardSerializer(ProductCardSerializer):
    """Карточка в разделе «Аксессуары»: category — чтобы разложить их по вкладкам («Чехлы», «Стёкла»)."""

    category = CategoryBriefSerializer(read_only=True)

    class Meta(ProductCardSerializer.Meta):
        fields = [*ProductCardSerializer.Meta.fields, "category"]
        read_only_fields = fields


class AccessoryListSerializer(serializers.Serializer):
    """Новый список аксессуаров: ids — товары на продаже в нужном порядке, [] — убрать все."""

    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)

    def validate_ids(self, ids):
        ids = list(dict.fromkeys(ids))
        # Предварительная проверка до запроса товаров; точная — в сервисе
        limit = settings.PRODUCT_ACCESSORIES_MAX
        if len(ids) > limit:
            raise serializers.ValidationError(
                f"У товара может быть не больше {limit} аксессуаров.", code="too_many_accessories"
            )
        found = Product.objects.on_sale().in_bulk(ids)
        missing = [str(pk) for pk in ids if pk not in found]
        if missing:
            raise serializers.ValidationError(f"Нет товаров на продаже с id: {', '.join(missing)}.", code="does_not_exist")
        return [found[pk] for pk in ids]


class ProductPublicDetailSerializer(ProductCardSerializer):
    delivery_methods = DeliveryMethodSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    # Путь от корня до категории товара — «хлебные крошки». Пусто — товар без категории
    category_path = serializers.SerializerMethodField()
    # Только доступные в категории товара (in_category); недоступные скрыты
    characteristics = serializers.SerializerMethodField()
    # Кнопки вариантов: [{characteristic_id, name, options: [{value_id, value, product_id,
    # selected, exact, in_stock}]}]. Пусто — у товара нет вариантов. См. catalog/variants.py
    variants = serializers.SerializerMethodField()

    class Meta(ProductCardSerializer.Meta):
        fields = [
            *ProductCardSerializer.Meta.fields,
            "description",
            "category_path",
            "quantity",
            "images",
            "delivery_methods",
            "characteristics",
            "variants",
        ]
        read_only_fields = fields

    def get_category_path(self, product) -> list[dict]:
        if product.category_id is None:
            return []
        return CategoryBriefSerializer(category_tree(self.context).path(product.category_id), many=True).data

    def get_characteristics(self, product) -> list[dict]:
        rows = ProductCharacteristicSerializer(product.characteristics.all(), many=True, context=self.context).data
        return [row for row in rows if row["in_category"]]

    def get_variants(self, product) -> list[dict]:
        return variants.variant_options(product, get_tree=lambda: category_tree(self.context))
