from django.urls import path

from .views import CartRecommendationsView

urlpatterns = [
    path("cart/recommendations/", CartRecommendationsView.as_view(), name="me-cart-recommendations"),
]
