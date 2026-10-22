from django.urls import path

from .views import BoughtTogetherView

urlpatterns = [
    path(
        "products/<int:product_id>/bought-together/",
        BoughtTogetherView.as_view(),
        name="product-bought-together",
    ),
]
