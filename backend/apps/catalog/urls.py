from django.urls import path

from .views import ProductFeedView, ProductPublicDetailView

urlpatterns = [
    path("products/", ProductFeedView.as_view(), name="product-feed"),
    path("products/<int:pk>/", ProductPublicDetailView.as_view(), name="product-detail"),
]
