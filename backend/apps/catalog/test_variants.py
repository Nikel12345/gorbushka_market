from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.delivery.models import DeliveryMethod
from apps.shops.models import Shop
from apps.users.models import User

from .models import Characteristic, CharacteristicValue, Product, ProductCharacteristic, ProductGroup
from .variants import variant_options


class VariantsBase(APITestCase):
    """Ноутбук: цвет × ОЗУ × SSD, есть не все комбинации."""

    def setUp(self):
        self.shop = Shop.objects.create(name="Магазин", address="Адрес")
        self.staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)
        self.color = Characteristic.objects.create(name="Цвет", sort_order=1)
        self.ram = Characteristic.objects.create(name="ОЗУ", sort_order=2)
        self.ssd = Characteristic.objects.create(name="SSD", sort_order=3)
        self.silver = self.value(self.color, "Серебристый", 1)
        self.dark = self.value(self.color, "Тёмный", 2)
        self.ram8 = self.value(self.ram, "8 ГБ", 1)
        self.ram16 = self.value(self.ram, "16 ГБ", 2)
        self.ssd256 = self.value(self.ssd, "256 ГБ", 1)
        self.ssd512 = self.value(self.ssd, "512 ГБ", 2)
        self.group = ProductGroup.objects.create(name="Ноутбук X")
        self.group.axes.set([self.color, self.ram, self.ssd])

    def value(self, characteristic, value, sort_order):
        return CharacteristicValue.objects.create(characteristic=characteristic, value=value, sort_order=sort_order)

    def make_product(self, title, *values, group=None, **kwargs):
        defaults = {"price_usd": Decimal("100"), "quantity": 1}
        product = Product.objects.create(shop=self.shop, title=title, group=group, **{**defaults, **kwargs})
        for value in values:
            ProductCharacteristic.objects.create(product=product, characteristic=value.characteristic, value=value)
        return product

    def make_laptops(self):
        return [
            self.make_product("#1", self.silver, self.ram8, self.ssd256, group=self.group),
            self.make_product("#2", self.silver, self.ram8, self.ssd512, group=self.group),
            self.make_product("#3", self.silver, self.ram16, self.ssd512, group=self.group),
            self.make_product("#4", self.dark, self.ram8, self.ssd256, group=self.group),
            self.make_product("#5", self.dark, self.ram16, self.ssd512, group=self.group, quantity=0),
        ]


class VariantOptionsTests(VariantsBase):
    def options(self, product):
        rows = variant_options(Product.objects.with_characteristics().select_related("group").get(pk=product.pk))
        return {
            row["name"]: [(o["value"], o["product_id"], o["selected"], o["exact"]) for o in row["options"]]
            for row in rows
        }

    def test_buttons_lead_to_same_or_nearest_variant(self):
        p1, p2, p3, p4, p5 = self.make_laptops()

        self.assertEqual(
            self.options(p3),
            {
                "Цвет": [("Серебристый", p3.id, True, True), ("Тёмный", p5.id, False, True)],
                "ОЗУ": [("8 ГБ", p2.id, False, True), ("16 ГБ", p3.id, True, True)],
                # Серебристого 16/256 нет: ближайший с 256 — #1 (совпадает цвет), а не #4
                "SSD": [("256 ГБ", p1.id, False, False), ("512 ГБ", p3.id, True, True)],
            },
        )

    def test_tie_prefers_earlier_axis(self):
        p1, p2, p3, p4, p5 = self.make_laptops()

        # С #2 (серебристый 8/512) на тёмный: #4 совпадает по ОЗУ, #5 — по SSD; ОЗУ раньше
        self.assertEqual(self.options(p2)["Цвет"][1], ("Тёмный", p4.id, False, False))

    def test_archived_products_are_not_variants(self):
        p1, p2, p3, p4, p5 = self.make_laptops()
        Product.objects.filter(pk__in=[p4.id, p5.id]).update(status=Product.Status.ARCHIVED)

        self.assertEqual(self.options(p3)["Цвет"], [("Серебристый", p3.id, True, True)])

    def test_product_without_group_has_no_variants(self):
        product = self.make_product("Чехол", self.silver)

        self.assertEqual(variant_options(product), [])


class PublicDetailVariantsTests(VariantsBase):
    def test_detail_has_characteristics_and_variants(self):
        p1, p2, p3, p4, p5 = self.make_laptops()

        response = self.client.get(reverse("product-detail", args=[p5.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [(c["name"], c["value"]) for c in response.data["characteristics"]],
            [("Цвет", "Тёмный"), ("ОЗУ", "16 ГБ"), ("SSD", "512 ГБ")],
        )
        color = response.data["variants"][0]
        self.assertEqual(color["name"], "Цвет")
        self.assertEqual(
            color["options"],
            [
                {"value_id": self.silver.id, "value": "Серебристый", "product_id": p3.id,
                 "selected": False, "exact": True, "in_stock": True},
                {"value_id": self.dark.id, "value": "Тёмный", "product_id": p5.id,
                 "selected": True, "exact": True, "in_stock": False},
            ],
        )

    def test_detail_query_count_does_not_grow_with_group(self):
        self.make_laptops()
        product = Product.objects.filter(group=self.group).first()

        # товар, фото, способы, характеристики; оси группы, товары группы, их характеристики
        with self.assertNumQueries(7):
            self.client.get(reverse("product-detail", args=[product.id]))


class ProductVariantAdminTests(VariantsBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)
        self.pickup = DeliveryMethod.objects.get(code="pickup")

    def create(self, **data):
        payload = {"title": "Ноутбук", "price_usd": "100", "delivery_method_ids": [self.pickup.id], **data}
        return self.client.post(reverse("admin-product-list"), payload, format="json")

    def patch(self, product, **data):
        return self.client.patch(reverse("admin-product-detail", args=[product.id]), data, format="json")

    def test_create_variant(self):
        response = self.create(
            group_id=self.group.id,
            characteristic_value_ids=[self.ssd512.id, self.silver.id, self.ram8.id],
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["group"], {"id": self.group.id, "name": "Ноутбук X"})
        self.assertEqual(
            [(c["name"], c["value"]) for c in response.data["characteristics"]],
            [("Цвет", "Серебристый"), ("ОЗУ", "8 ГБ"), ("SSD", "512 ГБ")],
        )

    def test_variant_needs_all_axes(self):
        response = self.create(group_id=self.group.id, characteristic_value_ids=[self.silver.id])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "variant_axis_missing")
        self.assertIn("ОЗУ, SSD", response.data["detail"])
        self.assertFalse(Product.objects.exists())

    def test_same_variant_twice_is_rejected(self):
        self.make_product("Есть", self.silver, self.ram8, self.ssd256, group=self.group)

        response = self.create(
            group_id=self.group.id,
            characteristic_value_ids=[self.silver.id, self.ram8.id, self.ssd256.id],
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "variant_duplicate")
        self.assertIn("«Есть»", response.data["detail"])

    def test_archived_variant_does_not_block(self):
        self.make_product("Снят", self.silver, self.ram8, self.ssd256, group=self.group, status=Product.Status.ARCHIVED)

        response = self.create(
            group_id=self.group.id,
            characteristic_value_ids=[self.silver.id, self.ram8.id, self.ssd256.id],
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_two_values_of_one_characteristic_are_rejected(self):
        response = self.create(characteristic_value_ids=[self.silver.id, self.dark.id])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "characteristic_repeated")

    def test_characteristics_without_group(self):
        response = self.create(characteristic_value_ids=[self.dark.id])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["group"])
        self.assertEqual([c["value"] for c in response.data["characteristics"]], ["Тёмный"])

    def test_patch_replaces_characteristics(self):
        product = self.make_product("#1", self.silver, self.ram8, self.ssd256, group=self.group)

        response = self.patch(product, characteristic_value_ids=[self.dark.id, self.ram8.id, self.ssd256.id])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([c["value"] for c in response.data["characteristics"]], ["Тёмный", "8 ГБ", "256 ГБ"])
        self.assertEqual(product.characteristics.count(), 3)

    def test_patch_group_checks_existing_characteristics(self):
        product = self.make_product("Без памяти", self.silver)

        response = self.patch(product, group_id=self.group.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "variant_axis_missing")
        product.refresh_from_db()
        self.assertIsNone(product.group)

    def test_patch_leaves_group(self):
        product = self.make_product("#1", self.silver, self.ram8, self.ssd256, group=self.group)

        response = self.patch(product, group_id=None)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertIsNone(product.group)
        self.assertEqual(product.characteristics.count(), 3)

    def test_list_filters_by_group(self):
        in_group = self.make_product("#1", self.silver, self.ram8, self.ssd256, group=self.group)
        self.make_product("Другой")

        response = self.client.get(reverse("admin-product-list"), {"group": self.group.id})

        self.assertEqual([p["id"] for p in response.data["results"]], [in_group.id])


class ProductGroupAdminTests(VariantsBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def detail_url(self):
        return reverse("admin-product-group-detail", args=[self.group.id])

    def test_create_group(self):
        response = self.client.post(
            reverse("admin-product-group-list"),
            {"name": "iPhone 13", "axis_ids": [self.color.id, self.ram.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual([a["name"] for a in response.data["axes"]], ["Цвет", "ОЗУ"])

    def test_group_needs_axes(self):
        response = self.client.post(reverse("admin-product-group-list"), {"name": "X", "axis_ids": []}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_groups(self):
        ProductGroup.objects.create(name="iPhone 13")

        response = self.client.get(reverse("admin-product-group-list"), {"q": "ноутбук"})

        self.assertEqual([g["name"] for g in response.data["results"]], ["Ноутбук X"])

    def test_new_axis_must_be_filled_in_products(self):
        self.group.axes.set([self.color])
        self.make_product("Чёрный ноутбук", self.silver, group=self.group)

        response = self.client.patch(self.detail_url(), {"axis_ids": [self.color.id, self.ram.id]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "variant_axis_missing")
        self.assertEqual(list(self.group.axes.all()), [self.color])

    def test_removing_axis_must_keep_variants_distinct(self):
        self.make_laptops()

        response = self.client.patch(self.detail_url(), {"axis_ids": [self.color.id]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "variant_duplicate")

    def test_change_axes(self):
        self.group.axes.set([self.color])
        self.make_product("A", self.silver, self.ram8, group=self.group)
        self.make_product("B", self.dark, self.ram8, group=self.group)

        response = self.client.patch(self.detail_url(), {"axis_ids": [self.color.id, self.ram.id]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([a["name"] for a in response.data["axes"]], ["Цвет", "ОЗУ"])

    def test_not_staff_is_403(self):
        self.client.force_login(User.objects.create_user(email="buyer@example.com", password="x"))

        for url in [reverse("admin-product-group-list"), self.detail_url(), reverse("admin-characteristic-list")]:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)


class CharacteristicAdminTests(VariantsBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def values_url(self, characteristic):
        return reverse("admin-characteristic-values", args=[characteristic.id])

    def test_list_with_values(self):
        response = self.client.get(reverse("admin-characteristic-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([c["name"] for c in response.data], ["Цвет", "ОЗУ", "SSD"])
        self.assertEqual([v["value"] for v in response.data[0]["values"]], ["Серебристый", "Тёмный"])

    def test_create_characteristic(self):
        response = self.client.post(reverse("admin-characteristic-list"), {"name": "SIM"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_value(self):
        response = self.client.post(self.values_url(self.color), {"value": "Розовый", "sort_order": 3}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.color.values.filter(value="Розовый").exists())

    def test_same_value_in_other_spelling_is_rejected(self):
        self.value(self.color, "Чёрный", 3)

        response = self.client.post(self.values_url(self.color), {"value": "черный"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("value", response.data)

    def test_same_name_in_other_case_is_rejected(self):
        response = self.client.post(reverse("admin-characteristic-list"), {"name": "цвет"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductDjangoAdminVariantsTests(VariantsBase):
    def test_pages_open(self):
        self.make_laptops()
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))

        for url in [
            reverse("admin:catalog_productgroup_changelist"),
            reverse("admin:catalog_productgroup_change", args=[self.group.id]),
            reverse("admin:catalog_productgroup_add"),
            reverse("admin:catalog_characteristic_changelist"),
            reverse("admin:catalog_characteristic_change", args=[self.color.id]),
            reverse("admin:catalog_product_add"),
        ]:
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK, url)

    def test_group_axes_are_checked(self):
        self.make_laptops()
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))

        response = self.client.post(
            reverse("admin:catalog_productgroup_change", args=[self.group.id]),
            {"name": "Ноутбук X", "axes": [self.color.id], "products-TOTAL_FORMS": "0", "products-INITIAL_FORMS": "0"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "не различаются по Цвет")
        self.assertEqual(self.group.axes.count(), 3)

    def test_inline_rejects_duplicate_variant(self):
        self.make_product("Есть", self.silver, self.ram8, self.ssd256, group=self.group)
        product = self.make_product("Новый", group=None)
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))
        url = reverse("admin:catalog_product_change", args=[product.id])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        data = {
            "shop": self.shop.id,
            "title": "Новый",
            "description": "",
            "price_usd": "100",
            "quantity": 1,
            "status": "active",
            "group": self.group.id,
            "images-TOTAL_FORMS": "0",
            "images-INITIAL_FORMS": "0",
            "characteristics-TOTAL_FORMS": "3",
            "characteristics-INITIAL_FORMS": "0",
        }
        for index, value in enumerate([self.silver, self.ram8, self.ssd256]):
            data[f"characteristics-{index}-value"] = value.id
            data[f"characteristics-{index}-product"] = product.id

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)  # форма с ошибкой
        self.assertContains(response, "уже есть товар с такими значениями")
        product.refresh_from_db()
        self.assertIsNone(product.group)

        data["characteristics-2-value"] = self.ssd512.id
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(product.characteristics.count(), 3)
