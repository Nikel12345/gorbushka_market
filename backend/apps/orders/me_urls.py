from django.urls import path

from .views import (
    BuyerOrderDetailView,
    BuyerOrderListView,
    BuyerOrderStatusView,
    BuyerPurchaseDetailView,
    BuyerPurchaseListView,
    CheckoutQuoteView,
    CheckoutView,
)

urlpatterns = [
    path("orders/", BuyerOrderListView.as_view(), name="me-order-list"),
    path("orders/<int:pk>/", BuyerOrderDetailView.as_view(), name="me-order-detail"),
    path("orders/<int:pk>/status/", BuyerOrderStatusView.as_view(), name="me-order-status"),
    path("purchases/", BuyerPurchaseListView.as_view(), name="me-purchase-list"),
    path("purchases/<int:pk>/", BuyerPurchaseDetailView.as_view(), name="me-purchase-detail"),
    path("checkout/", CheckoutView.as_view(), name="me-checkout"),
    path("checkout/quote/", CheckoutQuoteView.as_view(), name="me-checkout-quote"),
]
