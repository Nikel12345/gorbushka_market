from django.urls import path

from .views import CartItemDetailView, CartItemListView, CartView

urlpatterns = [
    path("cart/", CartView.as_view(), name="me-cart"),
    path("cart/items/", CartItemListView.as_view(), name="me-cart-items"),
    # Позиция адресуется id товара: фронт знает его из карточки, отдельный id позиции не нужен
    path("cart/items/<int:product_id>/", CartItemDetailView.as_view(), name="me-cart-item"),
]
