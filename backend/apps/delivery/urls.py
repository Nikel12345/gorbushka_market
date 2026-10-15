from django.urls import path

from .views import DeliveryMethodListView, DeliveryMethodSlotsView

urlpatterns = [
    path("methods/", DeliveryMethodListView.as_view(), name="delivery-method-list"),
    path("methods/<int:method_id>/slots/", DeliveryMethodSlotsView.as_view(), name="delivery-method-slots"),
]
