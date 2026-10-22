from django.urls import path

from .views import UsdRateView

urlpatterns = [
    path("usd/", UsdRateView.as_view(), name="currency-usd"),
]
