from decimal import Decimal

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.shops.models import Shop
from apps.users.models import User

from .models import (
    Category,
    Characteristic,
    CharacteristicValue,
    Product,
    ProductAccessory,
    ProductCharacteristic,
    ProductGroup,
)


class AccessoriesBase(APITestCase):
    """iPhone — группа из двух цветов, к ней чехлы, стекло и зарядка."""

    def setUp(self):
        self.shop = Shop.objects.create(name="Магазин", address="Адрес")
        self.staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)
        self.color = Characteristic.objects.create(name="Цвет")
        self.black = CharacteristicValue.objects.create(characteristic=self.color, value="Чёрный")
        self.white = CharacteristicValue.objects.create(characteristic=self.color, value="Белый")
        self.iphones = ProductGroup.objects.create(name="iPhone 16")
        self.iphones.axes.set([self.color])
        self.iphone_black = self.make("iPhone 16 чёрный", self.black, group=self.iphones)
        self.iphone_white = self.make("iPhone 16 белый", self.white, group=self.iphones)
        self.cases = Category.objects.create(name="Чехлы")
        self.case = self.make("Чехол", category=self.cases)
        self.glass = self.make("Стекло")
        self.charger = self.make("Зарядка", quantity=0)

    def make(self, title, *values, **kwargs):
        product = Product.objects.create(shop=self.shop, title=title, price_usd=Decimal("10"), **kwargs)
        for value in values:
            ProductCharacteristic.objects.create(product=product, characteristic=value.characteristic, value=value)
        return product

    def link(self, accessory, position, *, group=None, product=None):
        return ProductAccessory.objects.create(group=group, product=product, accessory=accessory, position=position)

    def titles(self, product):
        response = self.client.get(reverse("product-accessories", args=[product.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return [card["title"] for card in response.data]


class PublicAccessoriesTests(AccessoriesBase):
    def test_group_list_shared_by_all_variants_in_order(self):
        self.link(self.glass, 1, group=self.iphones)
        self.link(self.case, 0, group=self.iphones)
        new_variant = self.make("iPhone 16 розовый", group=self.iphones)

        self.assertEqual(self.titles(self.iphone_black), ["Чехол", "Стекло"])
        self.assertEqual(self.titles(self.iphone_white), ["Чехол", "Стекло"])
        self.assertEqual(self.titles(new_variant), ["Чехол", "Стекло"])

    def test_card_has_category_and_stock(self):
        self.link(self.case, 0, product=self.glass)
        self.link(self.charger, 1, product=self.glass)

        response = self.client.get(reverse("product-accessories", args=[self.glass.id]))

        case, charger = response.data
        self.assertEqual(case["category"], {"id": self.cases.id, "name": "Чехлы", "slug": self.cases.slug})
        self.assertEqual((case["in_stock"], charger["in_stock"]), (True, False))
        self.assertIsNone(charger["category"])

    def test_hides_off_sale_and_own_variants(self):
        self.link(self.case, 0, group=self.iphones)
        self.link(self.glass, 1, group=self.iphones)
        self.glass.status = Product.Status.ARCHIVED
        self.glass.save()
        self.case.group = self.iphones  # вошёл в группу уже после того, как стал её аксессуаром
        self.case.save()

        self.assertEqual(self.titles(self.iphone_black), [])

    def test_off_sale_product_404(self):
        self.iphone_black.status = Product.Status.ARCHIVED
        self.iphone_black.save()

        response = self.client.get(reverse("product-accessories", args=[self.iphone_black.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_two_queries(self):
        for position, accessory in enumerate([self.case, self.glass, self.charger]):
            self.link(accessory, position, group=self.iphones)

        with self.assertNumQueries(2):  # товар на продаже, карточки с магазином и категорией
            self.client.get(reverse("product-accessories", args=[self.iphone_black.id]))


class AdminAccessoriesTests(AccessoriesBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def put(self, product, ids):
        return self.client.put(reverse("admin-product-accessories", args=[product.id]), {"ids": ids}, format="json")

    def test_put_replaces_group_list(self):
        self.link(self.charger, 0, group=self.iphones)

        response = self.put(self.iphone_white, [self.glass.id, self.case.id, self.glass.id])

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual([card["title"] for card in response.data], ["Стекло", "Чехол"])
        self.assertEqual(self.titles(self.iphone_black), ["Стекло", "Чехол"])  # общий для группы
        self.assertFalse(ProductAccessory.objects.filter(product__isnull=False).exists())

    def test_put_own_list_and_clear(self):
        self.assertEqual(self.put(self.case, [self.glass.id]).status_code, status.HTTP_200_OK)
        self.assertEqual(self.titles(self.case), ["Стекло"])

        response = self.client.get(reverse("admin-product-accessories", args=[self.case.id]))
        self.assertEqual([card["title"] for card in response.data], ["Стекло"])

        self.assertEqual(self.put(self.case, []).data, [])
        self.assertFalse(ProductAccessory.objects.exists())

    def test_same_model_rejected(self):
        response = self.put(self.iphone_black, [self.case.id, self.iphone_white.id])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "accessory_same_model")
        self.assertEqual(self.put(self.case, [self.case.id]).data["code"], "accessory_same_model")
        self.assertFalse(ProductAccessory.objects.exists())

    def test_off_sale_or_missing_rejected(self):
        self.glass.status = Product.Status.ARCHIVED
        self.glass.save()

        response = self.put(self.case, [self.glass.id, 999])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ids", response.data)

    @override_settings(PRODUCT_ACCESSORIES_MAX=1)
    def test_limit(self):
        response = self.put(self.case, [self.glass.id, self.charger.id])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["ids"][0].code, "too_many_accessories")

    def test_staff_only(self):
        self.client.force_login(User.objects.create_user(email="buyer@example.com", password="x"))

        self.assertEqual(self.put(self.case, [self.glass.id]).status_code, status.HTTP_403_FORBIDDEN)


class DjangoAdminAccessoriesTests(AccessoriesBase):
    def test_group_inline_checks_same_model(self):
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))
        url = reverse("admin:catalog_productgroup_change", args=[self.iphones.id])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        data = {
            "name": "iPhone 16",
            "axes": [self.color.id],
            "products-TOTAL_FORMS": "0",
            "products-INITIAL_FORMS": "0",
            "accessory_links-TOTAL_FORMS": "1",
            "accessory_links-INITIAL_FORMS": "0",
            "accessory_links-0-accessory": self.iphone_white.id,
            "accessory_links-0-position": "0",
        }

        response = self.client.post(url, data)

        self.assertContains(response, "вариант этого же товара")
        data["accessory_links-0-accessory"] = self.case.id
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.titles(self.iphone_black), ["Чехол"])


class GroupChangeTests(AccessoriesBase):
    """Смена группы через PATCH товара: аксессуары, которые товар показывал, не пропадают."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def set_group(self, product, group):
        url = reverse("admin-product-detail", args=[product.id])
        response = self.client.patch(url, {"group_id": group.id if group else None}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_joining_group_appends_own_to_group(self):
        pink = self.make("iPhone 16 розовый", CharacteristicValue.objects.create(characteristic=self.color, value="Розовый"))
        self.link(self.case, 0, group=self.iphones)
        self.link(self.glass, 0, product=pink)
        self.link(self.case, 1, product=pink)  # уже есть у группы — не повторяется
        self.link(self.iphone_white, 2, product=pink)  # вариант группы — не аксессуар

        self.set_group(pink, self.iphones)

        self.assertEqual(self.titles(self.iphone_black), ["Чехол", "Стекло"])
        self.assertFalse(pink.accessory_links.exists())

    def test_leaving_group_keeps_copy(self):
        self.link(self.case, 0, group=self.iphones)
        self.link(self.glass, 1, group=self.iphones)

        self.set_group(self.iphone_white, None)

        self.assertEqual(self.titles(self.iphone_white), ["Чехол", "Стекло"])
        self.assertEqual(self.titles(self.iphone_black), ["Чехол", "Стекло"])
