from django.urls import path

from .views import ProductReviewListView

urlpatterns = [
    path("products/<int:product_id>/reviews/", ProductReviewListView.as_view(), name="product-reviews"),
]
