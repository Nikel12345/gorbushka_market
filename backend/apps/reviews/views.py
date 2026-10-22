from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

from apps.catalog.models import Product

from . import services
from .filters import ReviewFilter
from .models import Review
from .pagination import ReviewPagination
from .serializers import ReviewAdminSerializer, ReviewSerializer


class ReviewListMixin:
    """Единые фильтры и курсорная пагинация для любого списка отзывов."""

    filter_backends = [DjangoFilterBackend]
    filterset_class = ReviewFilter
    pagination_class = ReviewPagination


# --- Витрина ---


class ProductReviewListView(ReviewListMixin, generics.ListAPIView):
    """Отзывы о товаре на продаже: ?rating=, ?sort=, курсор. Снятый с продажи товар — 404."""

    permission_classes = [AllowAny]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        product_id = self.kwargs["product_id"]
        if not Product.objects.on_sale().filter(pk=product_id).exists():
            raise Http404
        return Review.objects.filter(product_id=product_id).with_details()


# --- Покупатель ---


class MyReviewsMixin:
    """Отзывы текущего пользователя: чужие не видны (404)."""

    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(author=self.request.user).with_details()


class MyReviewListCreateView(ReviewListMixin, MyReviewsMixin, generics.ListCreateAPIView):
    """GET — мои отзывы (?product=<id> — мой отзыв на товар), POST — оставить отзыв."""

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MyReviewDetailView(MyReviewsMixin, generics.RetrieveUpdateDestroyAPIView):
    """GET — отзыв, PATCH — изменить оценку и текст, DELETE — удалить."""

    http_method_names = ["get", "patch", "delete", "head", "options"]

    def perform_destroy(self, instance):
        services.delete_review(instance)


# --- Админка магазина ---


class ReviewAdminMixin:
    permission_classes = [IsAdminUser]
    serializer_class = ReviewAdminSerializer

    def get_queryset(self):
        return Review.objects.with_details()


class ReviewAdminListView(ReviewListMixin, ReviewAdminMixin, generics.ListAPIView):
    """Все отзывы (в том числе о снятых с продажи товарах): ?product=, ?rating=, ?sort=, курсор."""


class ReviewAdminDetailView(ReviewAdminMixin, generics.RetrieveDestroyAPIView):
    """GET — отзыв, DELETE — удалить (модерация). Текст чужого отзыва не правится."""

    def perform_destroy(self, instance):
        services.delete_review(instance)
