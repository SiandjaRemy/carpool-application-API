from django.urls import path, include

from rest_framework_nested import routers

from reservations import views

# Existing routers
router = routers.DefaultRouter()

router.register("reservations", views.ReservationgModelViewet, basename="reservations")


urlpatterns = [
    path("", include(router.urls)),
]
