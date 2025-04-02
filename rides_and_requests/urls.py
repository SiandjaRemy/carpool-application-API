from rest_framework.routers import DefaultRouter

from django.urls import path, include

from rides_and_requests import views

router = DefaultRouter()

router.register("rides", views.RideModelViewset, basename="rides")

urlpatterns = [
    path("", include(router.urls)),
]