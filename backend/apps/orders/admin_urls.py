from django.urls import path

from .views import OrderAdminDetailView, OrderAdminListView, OrderAdminStatusView

urlpatterns = [
    path("orders/", OrderAdminListView.as_view(), name="admin-order-list"),
    path("orders/<int:pk>/", OrderAdminDetailView.as_view(), name="admin-order-detail"),
    path("orders/<int:pk>/status/", OrderAdminStatusView.as_view(), name="admin-order-status"),
]
