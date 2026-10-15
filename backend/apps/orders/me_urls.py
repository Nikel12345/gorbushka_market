from django.urls import path

from .views import BuyerOrderListView

urlpatterns = [
    path("orders/", BuyerOrderListView.as_view(), name="me-order-list"),
]
