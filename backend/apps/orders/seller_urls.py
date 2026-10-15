from django.urls import path

from .views import SellerOrderListView

urlpatterns = [
    path("shops/<int:shop_id>/orders/", SellerOrderListView.as_view(), name="seller-order-list"),
]
