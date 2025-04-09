from rest_framework.routers import DefaultRouter

from django.urls import path, include

from rides import views

router = DefaultRouter()

router.register("rides", views.RideModelViewset, basename="rides")

urlpatterns = [
    path("", include(router.urls)),
]