from django.urls import path

from .views import SellerProfileView, SellerShopDetailView, SellerShopListCreateView

urlpatterns = [
    path("profile/", SellerProfileView.as_view(), name="seller-profile"),
    path("shops/", SellerShopListCreateView.as_view(), name="seller-shop-list"),
    path("shops/<int:shop_id>/", SellerShopDetailView.as_view(), name="seller-shop-detail"),
]
