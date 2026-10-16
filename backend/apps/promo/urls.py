from django.urls import path

from .views import FeedPromoView

urlpatterns = [
    path("feed/", FeedPromoView.as_view(), name="promo-feed"),
]
