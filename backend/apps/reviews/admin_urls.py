from django.urls import path

from .views import ReviewAdminDetailView, ReviewAdminListView

urlpatterns = [
    path("reviews/", ReviewAdminListView.as_view(), name="admin-review-list"),
    path("reviews/<int:pk>/", ReviewAdminDetailView.as_view(), name="admin-review-detail"),
]
