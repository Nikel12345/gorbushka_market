from django.urls import path

from .views import CategoryListView, ProductFeedView, ProductPublicDetailView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("products/", ProductFeedView.as_view(), name="product-feed"),
    path("products/<int:pk>/", ProductPublicDetailView.as_view(), name="product-detail"),
]
