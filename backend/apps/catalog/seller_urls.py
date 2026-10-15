from django.urls import path

from .views import SellerProductDetailView, SellerProductListCreateView

urlpatterns = [
    path(
        "shops/<int:shop_id>/products/",
        SellerProductListCreateView.as_view(),
        name="seller-product-list",
    ),
    path(
        "shops/<int:shop_id>/products/<int:pk>/",
        SellerProductDetailView.as_view(),
        name="seller-product-detail",
    ),
]
