from rest_framework.routers import DefaultRouter

from django.urls import path, include

from ride_alerts import views

router = DefaultRouter()

router.register("alerts", views.RideAlertModelViewset, basename="alerts")

urlpatterns = [
    path("", include(router.urls)),
]