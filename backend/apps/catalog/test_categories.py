from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.slugs import slugify_ru
from apps.delivery.models import DeliveryMethod
from apps.shops.models import Shop
from apps.users.models import User

from .models import Category, Characteristic, CharacteristicValue, Product, ProductCharacteristic, ProductGroup


class CategoriesBase(APITestCase):
    """
    Гаджеты
    ├─ Смартфоны
    └─ Часы
    Аудио
    """

    def setUp(self):
        self.shop = Shop.objects.create(name="Магазин", address="Адрес")
        self.staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)
        self.gadgets = Category.objects.create(name="Гаджеты", sort_order=1)
        self.phones = Category.objects.create(name="Смартфоны", parent=self.gadgets, sort_order=1)
        self.watches = Category.objects.create(name="Часы", parent=self.gadgets, sort_order=2)
        self.audio = Category.objects.create(name="Аудио", sort_order=2)

    def make_product(self, category=None, **kwargs):
        defaults = {"title": "Товар", "price_usd": Decimal("100")}
        return Product.objects.create(shop=self.shop, category=category, **{**defaults, **kwargs})


class CategoryTreeApiTests(CategoriesBase):
    def test_flat_list_in_tree_order(self):
        self.make_product(self.phones)
        self.make_product(self.phones)
        self.make_product(self.watches)
        self.make_product(self.gadgets)  # товар можно положить и в раздел с подкатегориями
        self.make_product(self.phones, status=Product.Status.ARCHIVED)

        response = self.client.get(reverse("category-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [(c["name"], c["parent_id"], c["depth"], c["products_count"]) for c in response.data],
            [
                ("Гаджеты", None, 0, 4),
                ("Смартфоны", self.gadgets.id, 1, 2),
                ("Часы", self.gadgets.id, 1, 1),
                ("Аудио", None, 0, 0),
            ],
        )

    def test_list_takes_two_queries(self):
        with self.assertNumQueries(2):  # категории, число товаров
            self.client.get(reverse("category-list"))

    def test_feed_filter_includes_subcategories(self):
        phone = self.make_product(self.phones, title="Телефон")
        watch = self.make_product(self.watches, title="Часы")
        self.make_product(self.audio, title="Колонка")
        self.make_product(title="Без категории")

        response = self.client.get(reverse("product-feed"), {"category": self.gadgets.id})

        self.assertEqual({p["id"] for p in response.data["results"]}, {phone.id, watch.id})
        response = self.client.get(reverse("product-feed"), {"category": self.phones.id})
        self.assertEqual([p["id"] for p in response.data["results"]], [phone.id])

    def test_feed_filter_by_unknown_category_is_empty(self):
        self.make_product(self.phones)

        response = self.client.get(reverse("product-feed"), {"category": 999})

        self.assertEqual(response.data["results"], [])

    def test_detail_has_category_path(self):
        product = self.make_product(self.phones)

        response = self.client.get(reverse("product-detail", args=[product.id]))

        self.assertEqual(
            response.data["category_path"],
            [
                {"id": self.gadgets.id, "name": "Гаджеты", "slug": "gadzhety"},
                {"id": self.phones.id, "name": "Смартфоны", "slug": "smartfony"},
            ],
        )

    def test_detail_without_category(self):
        product = self.make_product()

        response = self.client.get(reverse("product-detail", args=[product.id]))

        self.assertEqual(response.data["category_path"], [])


class CategoryAdminApiTests(CategoriesBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def detail_url(self, category):
        return reverse("admin-category-detail", args=[category.id])

    def test_create_generates_slug(self):
        response = self.client.post(
            reverse("admin-category-list"), {"name": "Экшн-камеры", "parent_id": self.gadgets.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["slug"], "ekshn-kamery")
        self.assertEqual(response.data["depth"], 1)
        self.assertEqual(Category.objects.get(pk=response.data["id"]).parent, self.gadgets)

    def test_same_slug_gets_number(self):
        response = self.client.post(reverse("admin-category-list"), {"name": "Смартфоны"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["slug"], "smartfony-2")

    def test_rename_keeps_slug(self):
        response = self.client.patch(self.detail_url(self.phones), {"name": "Телефоны"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "smartfony")

    def test_same_name_among_siblings_is_rejected(self):
        response = self.client.post(
            reverse("admin-category-list"), {"name": "смартфоны", "parent_id": self.gadgets.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_move(self):
        response = self.client.patch(self.detail_url(self.watches), {"parent_id": self.audio.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.watches.refresh_from_db()
        self.assertEqual(self.watches.parent, self.audio)

    def test_move_to_root(self):
        response = self.client.patch(self.detail_url(self.watches), {"parent_id": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["depth"], 0)

    def test_move_into_own_subcategory_is_rejected(self):
        for parent in [self.phones, self.gadgets]:
            response = self.client.patch(self.detail_url(self.gadgets), {"parent_id": parent.id}, format="json")

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["code"], "category_cycle")

    def test_delete_empty(self):
        response = self.client.delete(self.detail_url(self.audio))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=self.audio.pk).exists())

    def test_delete_with_subcategories_is_rejected(self):
        response = self.client.delete(self.detail_url(self.gadgets))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "category_not_empty")

    def test_delete_with_products_is_rejected(self):
        self.make_product(self.audio)

        response = self.client.delete(self.detail_url(self.audio))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "category_not_empty")

    def test_delete_frees_archived_products(self):
        archived = self.make_product(self.audio, status=Product.Status.ARCHIVED)

        response = self.client.delete(self.detail_url(self.audio))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        archived.refresh_from_db()
        self.assertIsNone(archived.category)

    def test_product_category(self):
        pickup = DeliveryMethod.objects.get(code="pickup")
        response = self.client.post(
            reverse("admin-product-list"),
            {"title": "Телефон", "price_usd": "100", "delivery_method_ids": [pickup.id], "category_id": self.phones.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["category"], {"id": self.phones.id, "name": "Смартфоны", "slug": "smartfony"})

        url = reverse("admin-product-detail", args=[response.data["id"]])
        response = self.client.patch(url, {"category_id": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["category"])

    def test_admin_products_filter_by_category(self):
        phone = self.make_product(self.phones)
        self.make_product(self.audio)

        response = self.client.get(reverse("admin-product-list"), {"category": self.gadgets.id})

        self.assertEqual([p["id"] for p in response.data["results"]], [phone.id])

    def test_not_staff_is_403(self):
        self.client.force_login(User.objects.create_user(email="buyer@example.com", password="x"))

        self.assertEqual(self.client.get(reverse("admin-category-list")).status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.post(reverse("admin-category-list"), {"name": "X"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CategoryDjangoAdminTests(CategoriesBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))

    def test_pages_open(self):
        for url in [
            reverse("admin:catalog_category_changelist"),
            reverse("admin:catalog_category_add"),
            reverse("admin:catalog_category_change", args=[self.phones.id]),
        ]:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK, url)

    def test_move_into_own_subcategory_is_rejected(self):
        response = self.client.post(
            reverse("admin:catalog_category_change", args=[self.gadgets.id]),
            {"name": "Гаджеты", "parent": self.phones.id, "slug": "gadzhety", "sort_order": 1},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Нельзя перенести категорию внутрь неё самой")


class SlugifyRuTests(APITestCase):
    def test_transliteration(self):
        self.assertEqual(slugify_ru("Смартфоны и гаджеты"), "smartfony-i-gadzhety")
        self.assertEqual(slugify_ru("Объективы"), "obektivy")
        self.assertEqual(slugify_ru("ТВ-приставки 4K"), "tv-pristavki-4k")


class CategoryCharacteristicsBase(CategoriesBase):
    """Цвет — общий, «Память» — у гаджетов (наследуют смартфоны и часы), «Тип» — у аудио."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)
        self.pickup = DeliveryMethod.objects.get(code="pickup")
        self.color = Characteristic.objects.create(name="Цвет")
        self.memory = Characteristic.objects.create(name="Память", category=self.gadgets)
        self.kind = Characteristic.objects.create(name="Тип", category=self.audio)
        self.black = CharacteristicValue.objects.create(characteristic=self.color, value="Чёрный")
        self.gb128 = CharacteristicValue.objects.create(characteristic=self.memory, value="128 ГБ")
        self.gb256 = CharacteristicValue.objects.create(characteristic=self.memory, value="256 ГБ")
        self.tws = CharacteristicValue.objects.create(characteristic=self.kind, value="TWS")

    def create_product(self, **data):
        payload = {"title": "Товар", "price_usd": "100", "delivery_method_ids": [self.pickup.id], **data}
        return self.client.post(reverse("admin-product-list"), payload, format="json")

    def make_with(self, category, *values, **kwargs):
        product = self.make_product(category, **kwargs)
        for value in values:
            ProductCharacteristic.objects.create(product=product, characteristic=value.characteristic, value=value)
        return product


class CharacteristicCategoryTests(CategoryCharacteristicsBase):
    def test_list_for_category_has_global_and_inherited(self):
        response = self.client.get(reverse("admin-characteristic-list"), {"category": self.phones.id})

        self.assertEqual([c["name"] for c in response.data], ["Цвет", "Память"])
        self.assertEqual(response.data[1]["category"], {"id": self.gadgets.id, "name": "Гаджеты", "slug": "gadzhety"})

    def test_create_and_move_characteristic(self):
        response = self.client.post(
            reverse("admin-characteristic-list"), {"name": "Диагональ", "category_id": self.phones.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["category"]["id"], self.phones.id)

        url = reverse("admin-characteristic-detail", args=[response.data["id"]])
        response = self.client.patch(url, {"category_id": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["category"])

    def test_same_name_allowed_in_other_branch(self):
        response = self.client.post(
            reverse("admin-characteristic-list"), {"name": "Тип", "category_id": self.phones.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_same_name_in_branch_is_rejected(self):
        cases = [
            {"name": "цвет", "category_id": self.phones.id},  # общий «Цвет» виден смартфонам
            {"name": "Память", "category_id": self.phones.id},  # «Память» гаджетов выше
            {"name": "Тип"},  # общий «Тип» был бы виден аудио, где «Тип» уже есть
        ]
        for data in cases:
            response = self.client.post(reverse("admin-characteristic-list"), data, format="json")

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, data)
            self.assertIn("name", response.data)

    def test_product_takes_global_and_inherited(self):
        response = self.create_product(category_id=self.phones.id, characteristic_value_ids=[self.black.id, self.gb128.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(all(c["in_category"] for c in response.data["characteristics"]))

    def test_product_rejects_characteristic_of_other_branch(self):
        response = self.create_product(category_id=self.phones.id, characteristic_value_ids=[self.tws.id])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "characteristic_not_in_category")
        self.assertIn("Тип", response.data["detail"])

    def test_product_without_category_takes_only_global(self):
        self.assertEqual(self.create_product(characteristic_value_ids=[self.black.id]).status_code, 201)

        response = self.create_product(characteristic_value_ids=[self.gb128.id])

        self.assertEqual(response.data["code"], "characteristic_not_in_category")

    def test_moving_product_to_other_category_checks_characteristics(self):
        product = self.make_with(self.phones, self.gb128)
        url = reverse("admin-product-detail", args=[product.id])

        response = self.client.patch(url, {"category_id": self.audio.id}, format="json")

        self.assertEqual(response.data["code"], "characteristic_not_in_category")
        response = self.client.patch(url, {"category_id": self.audio.id, "characteristic_value_ids": []}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_moved_characteristic_is_hidden_not_blocked(self):
        product = self.make_with(self.phones, self.black, self.gb128)

        response = self.client.patch(
            reverse("admin-characteristic-detail", args=[self.memory.id]), {"category_id": self.audio.id}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        public = self.client.get(reverse("product-detail", args=[product.id])).data
        self.assertEqual([c["name"] for c in public["characteristics"]], ["Цвет"])
        admin = self.client.get(reverse("admin-product-detail", args=[product.id])).data
        self.assertEqual(
            [(c["name"], c["in_category"]) for c in admin["characteristics"]], [("Цвет", True), ("Память", False)]
        )

    def test_category_move_hides_variants(self):
        group = ProductGroup.objects.create(name="Телефон")
        group.axes.set([self.memory])
        first = self.make_with(self.phones, self.gb128, group=group)
        self.make_with(self.phones, self.gb256, group=group)
        detail = reverse("product-detail", args=[first.id])
        self.assertEqual(len(self.client.get(detail).data["variants"][0]["options"]), 2)

        # Смартфоны переехали в аудио: «Память» гаджетов им больше не доступна
        response = self.client.patch(
            reverse("admin-category-detail", args=[self.phones.id]), {"parent_id": self.audio.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(detail).data["variants"], [])

    def test_variants_skip_sibling_outside_branch(self):
        group = ProductGroup.objects.create(name="Телефон")
        group.axes.set([self.memory])
        first = self.make_with(self.phones, self.gb128, group=group)
        self.make_with(self.audio, self.gb256, group=group)  # в аудио «Память» недоступна

        options = self.client.get(reverse("product-detail", args=[first.id])).data["variants"][0]["options"]

        self.assertEqual([o["value"] for o in options], ["128 ГБ"])

    def test_delete_category_with_characteristics_is_rejected(self):
        response = self.client.delete(reverse("admin-category-detail", args=[self.audio.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "category_not_empty")


class GroupCategoryTests(CategoryCharacteristicsBase):
    def create_group(self, **data):
        return self.client.post(reverse("admin-product-group-list"), data, format="json")

    def group_url(self, group):
        return reverse("admin-product-group-detail", args=[group.id])

    def make_group(self, category, *axes):
        group = ProductGroup.objects.create(name="Группа", category=category)
        group.axes.set(axes)
        return group

    def test_create_group_in_category(self):
        response = self.create_group(name="Телефон", category_id=self.phones.id, axis_ids=[self.color.id, self.memory.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["category"], {"id": self.phones.id, "name": "Смартфоны", "slug": "smartfony"})

    def test_axis_must_be_available_in_group_category(self):
        cases = [
            {"category_id": self.phones.id, "axis_ids": [self.kind.id]},  # «Тип» — у аудио
            {"axis_ids": [self.memory.id]},  # группе без категории — только общие
            {"category_id": self.gadgets.id, "axis_ids": [self.color.id, self.kind.id]},
        ]
        for data in cases:
            response = self.create_group(name="Группа", **data)

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, data)
            self.assertEqual(response.data["code"], "variant_axis_not_in_category")

    def test_product_must_be_inside_group_category(self):
        group = self.make_group(self.gadgets, self.color)

        inside = self.create_product(category_id=self.watches.id, group_id=group.id, characteristic_value_ids=[self.black.id])
        outside = self.create_product(category_id=self.audio.id, group_id=group.id, characteristic_value_ids=[self.black.id])
        no_category = self.create_product(group_id=group.id, characteristic_value_ids=[self.black.id])

        self.assertEqual(inside.status_code, status.HTTP_201_CREATED, inside.data)
        self.assertEqual(outside.data["code"], "variant_product_outside_category")
        self.assertEqual(no_category.data["code"], "variant_product_outside_category")

    def test_group_without_category_takes_products_anywhere(self):
        group = self.make_group(None, self.color)

        response = self.create_product(category_id=self.audio.id, group_id=group.id, characteristic_value_ids=[self.black.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_change_group_category_checks_products_and_axes(self):
        group = self.make_group(self.gadgets, self.color)
        self.make_with(self.watches, self.black, group=group)

        narrower = self.client.patch(self.group_url(group), {"category_id": self.phones.id}, format="json")
        self.assertEqual(narrower.data["code"], "variant_product_outside_category")

        group.axes.set([self.memory])
        ProductCharacteristic.objects.create(product=group.products.get(), characteristic=self.memory, value=self.gb128)
        to_root = self.client.patch(self.group_url(group), {"category_id": None}, format="json")
        self.assertEqual(to_root.data["code"], "variant_axis_not_in_category")  # «Память» не общая

        group.refresh_from_db()
        self.assertEqual(group.category, self.gadgets)

    def test_move_group_to_wider_category(self):
        group = self.make_group(self.phones, self.color)
        self.make_with(self.phones, self.black, group=group)

        response = self.client.patch(self.group_url(group), {"category_id": self.gadgets.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["category"]["id"], self.gadgets.id)

    def test_groups_for_category(self):
        everywhere = self.make_group(None, self.color)
        gadgets = self.make_group(self.gadgets, self.color)
        phones = self.make_group(self.phones, self.color)
        self.make_group(self.watches, self.color)
        self.make_group(self.audio, self.color)

        response = self.client.get(reverse("admin-product-group-list"), {"category": self.phones.id})

        self.assertEqual({g["id"] for g in response.data["results"]}, {everywhere.id, gadgets.id, phones.id})

    def test_category_move_out_of_group_hides_variants(self):
        group = self.make_group(self.gadgets, self.color)
        first = self.make_with(self.phones, self.black, group=group)
        blue = CharacteristicValue.objects.create(characteristic=self.color, value="Синий")
        self.make_with(self.watches, blue, group=group)
        detail = reverse("product-detail", args=[first.id])
        self.assertEqual(len(self.client.get(detail).data["variants"][0]["options"]), 2)

        # Часы ушли в аудио — их товар теперь вне категории группы
        self.client.patch(reverse("admin-category-detail", args=[self.watches.id]), {"parent_id": self.audio.id}, format="json")
        self.assertEqual([o["value"] for o in self.client.get(detail).data["variants"][0]["options"]], ["Чёрный"])

        # Смартфоны ушли туда же — у самого товара вариантов нет
        self.client.patch(reverse("admin-category-detail", args=[self.phones.id]), {"parent_id": self.audio.id}, format="json")
        self.assertEqual(self.client.get(detail).data["variants"], [])

    def test_delete_category_with_groups_is_rejected(self):
        self.make_group(self.watches, self.color)

        response = self.client.delete(reverse("admin-category-detail", args=[self.watches.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "category_not_empty")

    def test_django_admin_checks_group_category(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))

        response = self.client.post(
            reverse("admin:catalog_productgroup_add"),
            {"name": "Группа", "category": self.audio.id, "axes": [self.memory.id],
             "products-TOTAL_FORMS": "0", "products-INITIAL_FORMS": "0"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Не подходят для категории")
        self.assertFalse(ProductGroup.objects.exists())
