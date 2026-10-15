from django.urls import path

from .views import ShopPublicDetailView

urlpatterns = [
    path("<int:shop_id>/", ShopPublicDetailView.as_view(), name="shop-detail"),
]
