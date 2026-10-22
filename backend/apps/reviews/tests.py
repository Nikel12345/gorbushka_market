from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Product
from apps.shops.models import Shop
from apps.users.models import User

from . import services
from .models import Review


class ReviewsBase(APITestCase):
    def setUp(self):
        self.shop = Shop.objects.create(name="Магазин", address="Адрес")
        self.product = Product.objects.create(shop=self.shop, title="Телефон", price_usd=Decimal("100"))
        self.user = User.objects.create_user(email="buyer@example.com", password="x", first_name="Анна")
        self.staff = User.objects.create_user(email="staff@example.com", password="x", is_staff=True)

    def make_user(self, email, **kwargs):
        return User.objects.create_user(email=email, password="x", **kwargs)

    def make_review(self, author, rating, product=None, **kwargs):
        return services.create_review(
            product=product or self.product, author=author, rating=rating, **{"comment": "Текст", **kwargs}
        )

    def post_review(self, **data):
        self.client.force_authenticate(self.user)
        return self.client.post(reverse("me-review-list"), {"product_id": self.product.id, **data}, format="json")

    def product_rating(self):
        self.product.refresh_from_db()
        return self.product.rating, self.product.reviews_count


class CreateReviewTests(ReviewsBase):
    def test_create_with_pros_cons_comment(self):
        response = self.post_review(rating=4, pros="Экран", cons="Батарея", comment="В целом доволен")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(
            {key: response.data[key] for key in ("product_id", "product_title", "author_name", "rating", "pros", "cons")},
            {"product_id": self.product.id, "product_title": "Телефон", "author_name": "Анна", "rating": 4,
             "pros": "Экран", "cons": "Батарея"},
        )
        self.assertEqual(self.product_rating(), (Decimal("4.00"), 1))

    def test_any_one_text_is_enough(self):
        for field in ("pros", "cons", "comment"):
            Review.objects.all().delete()

            response = self.post_review(rating=5, **{field: "Есть что сказать"})

            self.assertEqual(response.status_code, status.HTTP_201_CREATED, field)

    def test_text_is_required(self):
        response = self.post_review(rating=5, pros="  ", comment="")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["non_field_errors"], ["Напишите достоинства, недостатки или комментарий."])

    def test_rating_from_1_to_5(self):
        for rating in (0, 6, None):
            response = self.post_review(rating=rating, comment="Текст")

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, rating)
            self.assertIn("rating", response.data)

    def test_one_review_per_product(self):
        self.post_review(rating=5, comment="Первый")

        response = self.post_review(rating=1, comment="Второй")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "review_exists")
        self.assertEqual(self.product_rating(), (Decimal("5.00"), 1))

    def test_archived_product_cannot_be_reviewed(self):
        self.product.status = Product.Status.ARCHIVED
        self.product.save()

        response = self.post_review(rating=5, comment="Текст")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("product_id", response.data)

    def test_anonymous_cannot_review(self):
        response = self.client.post(reverse("me-review-list"), {"product_id": self.product.id, "rating": 5, "comment": "Текст"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_rating_is_average(self):
        self.make_review(self.make_user("a@example.com"), 5)
        self.make_review(self.make_user("b@example.com"), 4)
        self.make_review(self.make_user("c@example.com"), 4)

        self.assertEqual(self.product_rating(), (Decimal("4.33"), 3))


class MyReviewTests(ReviewsBase):
    def test_find_my_review_for_product(self):
        other_product = Product.objects.create(shop=self.shop, title="Другой", price_usd=Decimal("1"))
        mine = self.make_review(self.user, 5)
        self.make_review(self.user, 3, product=other_product)
        self.make_review(self.make_user("other@example.com"), 1)
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("me-review-list"), {"product": self.product.id})

        self.assertEqual([r["id"] for r in response.data["results"]], [mine.id])

    def test_update_recalculates_rating(self):
        review = self.make_review(self.user, 5)
        self.make_review(self.make_user("other@example.com"), 3)
        self.client.force_authenticate(self.user)

        response = self.client.patch(reverse("me-review-detail", args=[review.id]), {"rating": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.product_rating(), (Decimal("2.00"), 2))

    def test_update_cannot_clear_all_texts_or_move_review(self):
        other_product = Product.objects.create(shop=self.shop, title="Другой", price_usd=Decimal("1"))
        review = self.make_review(self.user, 5, pros="Экран", comment="")
        self.client.force_authenticate(self.user)
        url = reverse("me-review-detail", args=[review.id])

        cleared = self.client.patch(url, {"pros": ""}, format="json")
        moved = self.client.patch(url, {"product_id": other_product.id, "cons": "Батарея"}, format="json")

        self.assertEqual(cleared.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(moved.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual((review.product_id, review.pros, review.cons), (self.product.id, "Экран", "Батарея"))

    def test_delete_recalculates_rating(self):
        review = self.make_review(self.user, 5)
        self.client.force_authenticate(self.user)

        response = self.client.delete(reverse("me-review-detail", args=[review.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.product_rating(), (Decimal("0.00"), 0))

    def test_cannot_touch_others_review(self):
        review = self.make_review(self.make_user("other@example.com"), 5)
        self.client.force_authenticate(self.user)
        url = reverse("me-review-detail", args=[review.id])

        self.assertEqual(self.client.patch(url, {"rating": 1}, format="json").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_404_NOT_FOUND)


class ProductReviewListTests(ReviewsBase):
    def test_reviews_of_product_newest_first(self):
        first = self.make_review(self.make_user("a@example.com"), 5)
        second = self.make_review(self.make_user("b@example.com", first_name="Пётр"), 3)
        other_product = Product.objects.create(shop=self.shop, title="Другой", price_usd=Decimal("1"))
        self.make_review(self.user, 4, product=other_product)

        response = self.client.get(reverse("product-reviews", args=[self.product.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([r["id"] for r in response.data["results"]], [second.id, first.id])
        self.assertEqual([r["author_name"] for r in response.data["results"]], ["Пётр", "Покупатель"])
        self.assertNotIn("author_email", response.data["results"][0])

    def test_filter_and_sort_by_rating(self):
        for index, rating in enumerate([3, 5, 1, 5]):
            self.make_review(self.make_user(f"u{index}@example.com"), rating)
        url = reverse("product-reviews", args=[self.product.id])

        best = self.client.get(url, {"sort": "rating_desc"})
        good = self.client.get(url, {"rating": [4, 5]})

        self.assertEqual([r["rating"] for r in best.data["results"]], [5, 5, 3, 1])
        self.assertEqual([r["rating"] for r in good.data["results"]], [5, 5])

    def test_cursor_pages(self):
        for index in range(3):
            self.make_review(self.make_user(f"u{index}@example.com"), 5)
        url = reverse("product-reviews", args=[self.product.id])

        first = self.client.get(url, {"page_size": 2})
        second = self.client.get(url, {"page_size": 2, "cursor": first.data["next_cursor"]})

        self.assertEqual(len(first.data["results"]), 2)
        self.assertEqual(len(second.data["results"]), 1)
        self.assertIsNone(second.data["next_cursor"])

    def test_list_takes_two_queries(self):
        for index in range(3):
            self.make_review(self.make_user(f"u{index}@example.com"), 5)

        with self.assertNumQueries(2):  # товар на продаже, отзывы с названием товара и именем автора
            self.client.get(reverse("product-reviews", args=[self.product.id]))

    def test_archived_product_404(self):
        self.product.status = Product.Status.ARCHIVED
        self.product.save()

        response = self.client.get(reverse("product-reviews", args=[self.product.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_product_card_and_detail_have_rating(self):
        self.make_review(self.user, 5)
        self.make_review(self.make_user("other@example.com"), 4)

        feed = self.client.get(reverse("product-feed")).data["results"][0]
        detail = self.client.get(reverse("product-detail", args=[self.product.id])).data

        for data in (feed, detail):
            self.assertEqual((data["rating"], data["reviews_count"]), ("4.50", 2))


class ReviewAdminTests(ReviewsBase):
    def test_staff_only(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("admin-review-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_with_author_and_delete(self):
        review = self.make_review(self.user, 5)
        self.make_review(self.make_user("other@example.com"), 1)
        self.client.force_authenticate(self.staff)

        listed = self.client.get(reverse("admin-review-list"), {"rating": 5})
        deleted = self.client.delete(reverse("admin-review-detail", args=[review.id]))

        self.assertEqual(
            [(r["id"], r["author_email"]) for r in listed.data["results"]], [(review.id, "buyer@example.com")]
        )
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.product_rating(), (Decimal("1.00"), 1))

    def test_list_takes_one_query(self):
        for index in range(3):
            self.make_review(self.make_user(f"u{index}@example.com"), 5)
        self.client.force_authenticate(self.staff)

        with self.assertNumQueries(1):  # отзывы с названием товара, именем и email автора
            self.client.get(reverse("admin-review-list"))

    def test_staff_cannot_edit_text(self):
        review = self.make_review(self.user, 5)
        self.client.force_authenticate(self.staff)

        response = self.client.patch(reverse("admin-review-detail", args=[review.id]), {"rating": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ReviewDjangoAdminTests(ReviewsBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(User.objects.create_superuser(email="admin@example.com", password="x"))

    def form_data(self, **data):
        return {"product": self.product.id, "author": self.user.id, "rating": 5, "pros": "", "cons": "", "comment": "",
                **data}

    def test_add_checks_text_and_recalculates(self):
        empty = self.client.post(reverse("admin:reviews_review_add"), self.form_data())
        added = self.client.post(reverse("admin:reviews_review_add"), self.form_data(comment="Текст"))

        self.assertContains(empty, "Напишите достоинства, недостатки или комментарий.")
        self.assertEqual(added.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.product_rating(), (Decimal("5.00"), 1))

    def test_move_to_other_product_recalculates_both(self):
        review = self.make_review(self.user, 5)
        other_product = Product.objects.create(shop=self.shop, title="Другой", price_usd=Decimal("1"))

        self.client.post(
            reverse("admin:reviews_review_change", args=[review.id]),
            self.form_data(product=other_product.id, comment="Текст"),
        )

        other_product.refresh_from_db()
        self.assertEqual(self.product_rating(), (Decimal("0.00"), 0))
        self.assertEqual((other_product.rating, other_product.reviews_count), (Decimal("5.00"), 1))

    def test_bulk_delete_recalculates(self):
        self.make_review(self.user, 5)
        self.make_review(self.make_user("other@example.com"), 1)

        self.client.post(
            reverse("admin:reviews_review_changelist"),
            {"action": "delete_selected", "_selected_action": list(Review.objects.values_list("pk", flat=True)),
             "post": "yes"},
        )

        self.assertFalse(Review.objects.exists())
        self.assertEqual(self.product_rating(), (Decimal("0.00"), 0))
