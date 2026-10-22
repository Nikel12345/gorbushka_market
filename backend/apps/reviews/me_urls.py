from django.urls import path

from .views import MyReviewDetailView, MyReviewListCreateView

urlpatterns = [
    path("reviews/", MyReviewListCreateView.as_view(), name="me-review-list"),
    path("reviews/<int:pk>/", MyReviewDetailView.as_view(), name="me-review-detail"),
]
