from django.urls import path, include

from rest_framework_nested import routers

from carpool.qstash_tasks import QStashTaskView
from carpool.views import alert_views, request_views, reservation_views, ride_views


app_name = "carpool"

router = routers.DefaultRouter()

router.register("rides", ride_views.RideModelViewset, basename="rides")
router.register("alerts", alert_views.RideAlertModelViewset, basename="alerts")
router.register(
    "reservations", reservation_views.ReservationModelViewset, basename="reservations"
)


ride_router = routers.NestedDefaultRouter(
    router,
    "rides",
    lookup="rides",
)
ride_router.register(
    "requests", request_views.RideRequestModelViewset, basename="requests"
)


urlpatterns = [
    path("", include(router.urls)),
    path("", include(ride_router.urls)),
    path("tasks/<str:task_name>/", QStashTaskView.as_view(), name="qstash_tasks"),
]
