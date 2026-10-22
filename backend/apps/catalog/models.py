import os
import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.slugs import slugify_ru
from apps.currency.services import usd_to_rub
from apps.delivery.models import DeliveryMethod
from apps.shops.models import Shop

from .search import build_search_text


def product_image_upload_to(instance, filename):
    # Случайное имя: без коллизий и без утечки исходных имён файлов пользователей
    ext = os.path.splitext(filename)[1].lower()
    return f"products/{uuid.uuid4().hex}{ext}"


class Category(TimeStampedModel):
    """
    Категория каталога — дерево любой глубины. Товары можно класть в любой узел; раздел
    показывает товары категории вместе с подкатегориями. Обход дерева — catalog/categories.py.
    Перенос под другого родителя разрешён всегда (кроме переноса внутрь себя), удалить
    можно только категорию без подкатегорий и товаров на продаже (catalog/services.py).
    """

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="родительская категория",
    )
    name = models.CharField("название", max_length=100)
    # Часть адреса страницы раздела. Пусто при создании — генерируется из названия и дальше
    # не меняется при переименовании: старые ссылки продолжают работать.
    slug = models.SlugField("адрес", max_length=120, unique=True, blank=True)
    sort_order = models.PositiveSmallIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"
        ordering = ["sort_order", "name", "id"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self) -> str:
        base = slugify_ru(self.name)[:110] or "category"
        slug, number = base, 2
        while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug, number = f"{base}-{number}", number + 1
        return slug


class Characteristic(models.Model):
    """
    Характеристика товара: «Цвет», «Встроенная память». Значения — только из справочника
    (CharacteristicValue), чтобы «Чёрный» и «черный» не стали разными вариантами.
    Различают варианты товара (ProductGroup.axes); позже на них же лягут фильтры категорий.

    category — где характеристика доступна: в этой категории и всех её подкатегориях
    (CategoryTree.allows). Пусто — во всех категориях. При сохранении товара доступность
    проверяется строго (catalog/variants.py), а после переноса категорий или характеристики
    недоступное просто скрывается на витрине.
    """

    # Название уникально в пределах ветки категорий — проверяет сериализатор
    name = models.CharField("название", max_length=100)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="characteristics",
        verbose_name="категория",
        help_text="Пусто — во всех категориях. Иначе — в этой категории и её подкатегориях.",
    )
    # Порядок строк кнопок вариантов и характеристик в карточке
    sort_order = models.PositiveSmallIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "характеристика"
        verbose_name_plural = "характеристики"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class CharacteristicValue(models.Model):
    """Значение из справочника характеристики: «Чёрный» для «Цвет», «256 ГБ» для «Встроенная память»."""

    characteristic = models.ForeignKey(
        Characteristic,
        on_delete=models.CASCADE,
        related_name="values",
        verbose_name="характеристика",
    )
    value = models.CharField("значение", max_length=100)
    # Порядок кнопок: «512 ГБ» перед «1 ТБ», а не по алфавиту
    sort_order = models.PositiveSmallIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "значение характеристики"
        verbose_name_plural = "значения характеристик"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["characteristic", "value"], name="catalog_characteristic_value_unique"),
        ]

    def __str__(self):
        return f"{self.characteristic}: {self.value}"


class ProductGroup(TimeStampedModel):
    """
    Группа вариантов — товары одной модели («iPhone 13»), которые различаются значениями
    характеристик-осей (цвет, память). Своей страницы у группы нет: каждый вариант —
    отдельный товар, а кнопки вариантов строит catalog/variants.py по товарам группы.

    category — где лежат товары группы: в этой категории и её подкатегориях; оси — из
    характеристик, доступных в ней. Пусто — товары в любых категориях, оси — только общие.
    """

    name = models.CharField("название", max_length=255)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="product_groups",
        verbose_name="категория",
    )
    axes = models.ManyToManyField(Characteristic, related_name="+", verbose_name="различаются по")

    class Meta:
        verbose_name = "группа вариантов"
        verbose_name_plural = "группы вариантов"
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def on_sale(self):
        return self.filter(status=Product.Status.ACTIVE)

    def with_characteristics(self):
        return self.prefetch_related(
            models.Prefetch(
                "characteristics",
                queryset=ProductCharacteristic.objects.select_related("characteristic", "value"),
            )
        )

    def with_admin_details(self):
        """Всё, что выводит админка магазина по товару, без N+1."""
        return (
            self.select_related("category", "group")
            .prefetch_related("delivery_methods", "images")
            .with_characteristics()
        )


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "На продаже"
        # Товар «удалён» в админке магазина. Физически не удаляем: на него ссылаются заказы.
        ARCHIVED = "archived", "Удалён"

    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="магазин",
    )
    title = models.CharField("название", max_length=255)
    description = models.TextField("описание", blank=True)
    # Пусто — товар ещё не разложен по категориям: он есть в общей ленте, но ни в одном разделе
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="категория",
    )
    # Цена хранится в долларах; покупатель видит рубли — свойство price (apps/currency)
    price_usd = models.DecimalField(
        "цена, $",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    quantity = models.PositiveIntegerField("в наличии", default=1)
    # Обложка — кеш первого фото из ProductImage: лента, корзина и заказы читают её без
    # лишних запросов. Напрямую не меняется, её выставляют сервисы фото (catalog/services.py).
    image = models.ImageField("обложка", upload_to=product_image_upload_to, blank=True, max_length=255)
    # Какими способами можно получить товар. Задаётся в админке магазина при создании/редактировании,
    # из DeliveryMethod.objects.available_for_shop(shop).
    delivery_methods = models.ManyToManyField(
        DeliveryMethod,
        related_name="products",
        verbose_name="способы доставки",
        blank=True,
    )
    status = models.CharField(
        "статус",
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    # Группа вариантов. Пусто — у товара нет вариантов. Значения осей группы — в характеристиках
    # товара (ProductCharacteristic), правила — catalog/variants.py
    group = models.ForeignKey(
        ProductGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="группа вариантов",
    )
    # Кеш по отзывам (reviews.Review): средняя оценка (0 — отзывов нет) и их число.
    # Напрямую не меняются — их пересчитывает reviews.services после каждого изменения отзывов
    rating = models.DecimalField("оценка", max_digits=3, decimal_places=2, default=0, editable=False)
    reviews_count = models.PositiveIntegerField("отзывов", default=0, editable=False)
    # Нормализованный текст для поиска, заполняется в save(). См. catalog/search.py
    search_text = models.TextField(editable=False, blank=True, default="")

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["shop", "status"]),
            # Под сортировки публичной ленты (keyset-пагинация по полю + id)
            models.Index(fields=["status", "-created_at", "-id"], name="catalog_feed_new_idx"),
            models.Index(fields=["status", "price_usd", "id"], name="catalog_feed_price_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price_usd__gt=0), name="catalog_product_price_positive"),
        ]

    def __str__(self):
        return self.title

    @property
    def price(self) -> Decimal:
        """Цена в рублях по текущему курсу — её показывают покупателю и фиксируют в заказе."""
        return usd_to_rub(self.price_usd)

    def save(self, *args, **kwargs):
        self.search_text = build_search_text(self.title, self.description)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and {"title", "description"} & set(update_fields):
            kwargs["update_fields"] = {*update_fields, "search_text"}
        super().save(*args, **kwargs)


class ProductCharacteristic(models.Model):
    """
    Значение характеристики у товара. characteristic повторяет value.characteristic —
    так база сама не даёт товару два значения одной характеристики.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="characteristics",
        verbose_name="товар",
    )
    characteristic = models.ForeignKey(
        Characteristic,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="характеристика",
    )
    value = models.ForeignKey(
        CharacteristicValue,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name="значение",
    )

    class Meta:
        verbose_name = "характеристика товара"
        verbose_name_plural = "характеристики товара"
        ordering = ["characteristic__sort_order", "characteristic_id"]
        constraints = [
            models.UniqueConstraint(fields=["product", "characteristic"], name="catalog_product_characteristic_unique"),
        ]

    def __str__(self):
        return str(self.value)


class ProductImage(models.Model):
    """
    Фото товара. Порядок — по position (затем id), первое фото — обложка (Product.image).
    Позиции могут идти с пропусками. Файл удаляется с диска после удаления записи,
    когда транзакция закоммичена (catalog/signals.py).
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name="товар")
    image = models.ImageField("фото", upload_to=product_image_upload_to, max_length=255)
    position = models.PositiveIntegerField("порядок", default=0)
    created_at = models.DateTimeField("создано", auto_now_add=True)

    class Meta:
        verbose_name = "фото товара"
        verbose_name_plural = "фото товара"
        ordering = ["position", "id"]
        indexes = [models.Index(fields=["product", "position", "id"], name="catalog_image_order_idx")]

    def __str__(self):
        return self.image.name
