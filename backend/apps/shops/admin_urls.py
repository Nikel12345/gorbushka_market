from django.urls import path

from .views import ShopAdminView

urlpatterns = [
    path("shop/", ShopAdminView.as_view(), name="admin-shop"),
]
