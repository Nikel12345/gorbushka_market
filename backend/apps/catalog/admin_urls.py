from django.urls import path

from .views import (
    CategoryAdminDetailView,
    CategoryAdminListCreateView,
    CharacteristicAdminDetailView,
    CharacteristicAdminListCreateView,
    CharacteristicValueAdminCreateView,
    ProductAdminDetailView,
    ProductAdminListCreateView,
    ProductGroupAdminDetailView,
    ProductGroupAdminListCreateView,
    ProductImageAdminDetailView,
    ProductImageAdminListCreateView,
    ProductImageAdminOrderView,
)

urlpatterns = [
    path("categories/", CategoryAdminListCreateView.as_view(), name="admin-category-list"),
    path("categories/<int:pk>/", CategoryAdminDetailView.as_view(), name="admin-category-detail"),
    path("products/", ProductAdminListCreateView.as_view(), name="admin-product-list"),
    path("products/<int:pk>/", ProductAdminDetailView.as_view(), name="admin-product-detail"),
    path("products/<int:product_id>/images/", ProductImageAdminListCreateView.as_view(), name="admin-product-images"),
    path(
        "products/<int:product_id>/images/order/",
        ProductImageAdminOrderView.as_view(),
        name="admin-product-images-order",
    ),
    path(
        "products/<int:product_id>/images/<int:pk>/",
        ProductImageAdminDetailView.as_view(),
        name="admin-product-image-detail",
    ),
    path("characteristics/", CharacteristicAdminListCreateView.as_view(), name="admin-characteristic-list"),
    path(
        "characteristics/<int:pk>/",
        CharacteristicAdminDetailView.as_view(),
        name="admin-characteristic-detail",
    ),
    path(
        "characteristics/<int:characteristic_id>/values/",
        CharacteristicValueAdminCreateView.as_view(),
        name="admin-characteristic-values",
    ),
    path("product-groups/", ProductGroupAdminListCreateView.as_view(), name="admin-product-group-list"),
    path("product-groups/<int:pk>/", ProductGroupAdminDetailView.as_view(), name="admin-product-group-detail"),
]
