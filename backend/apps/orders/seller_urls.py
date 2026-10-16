from django.urls import path

from .views import SellerOrderDetailView, SellerOrderListView, SellerOrderStatusView

urlpatterns = [
    path("shops/<int:shop_id>/orders/", SellerOrderListView.as_view(), name="seller-order-list"),
    path("shops/<int:shop_id>/orders/<int:pk>/", SellerOrderDetailView.as_view(), name="seller-order-detail"),
    path(
        "shops/<int:shop_id>/orders/<int:pk>/status/",
        SellerOrderStatusView.as_view(),
        name="seller-order-status",
    ),
]
