from rest_framework.routers import DefaultRouter

from django.urls import path, include

from ride_requests import views

router = DefaultRouter()

router.register("requests", views.RideRequestModelViewset, basename="requests")

urlpatterns = [
    path("", include(router.urls)),
]