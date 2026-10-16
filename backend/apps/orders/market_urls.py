from django.urls import path

from .views import MarketOrderListView, MarketOrderStatusView

urlpatterns = [
    path("orders/", MarketOrderListView.as_view(), name="market-order-list"),
    path("orders/<int:pk>/status/", MarketOrderStatusView.as_view(), name="market-order-status"),
]
