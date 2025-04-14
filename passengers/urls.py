from rest_framework.routers import DefaultRouter

from django.urls import path, include

from passengers import views


urlpatterns = []

# urlpatterns = [
#     path("for_user/<uuid:user_pk>/", views.GetUserReviewGenericView.as_view(), name="get_reviews_for_user"),
#     path("for_transaction/", views.CreateReviewForTransactionGenericView.as_view(), name="create_reviews_for_transaction"),
#     path("for_transaction/<uuid:transaction_pk>", views.GetReviewsForTransactionGenericView.as_view(), name="get_reviews_for_transaction"),
# ]
