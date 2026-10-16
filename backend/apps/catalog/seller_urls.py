from django.urls import path

from .views import (
    SellerAllProductsView,
    SellerProductDetailView,
    SellerProductImageDetailView,
    SellerProductImageListCreateView,
    SellerProductImageOrderView,
    SellerProductListCreateView,
)

urlpatterns = [
    path("products/", SellerAllProductsView.as_view(), name="seller-all-products"),
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
    path(
        "shops/<int:shop_id>/products/<int:product_id>/images/",
        SellerProductImageListCreateView.as_view(),
        name="seller-product-images",
    ),
    path(
        "shops/<int:shop_id>/products/<int:product_id>/images/order/",
        SellerProductImageOrderView.as_view(),
        name="seller-product-images-order",
    ),
    path(
        "shops/<int:shop_id>/products/<int:product_id>/images/<int:pk>/",
        SellerProductImageDetailView.as_view(),
        name="seller-product-image-detail",
    ),
]
