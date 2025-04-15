from rest_framework.routers import DefaultRouter

from django.urls import path, include

from passengers import views


urlpatterns = []

urlpatterns = [
    path("register/", views.RegisterPassengerForRideGenericView.as_view(), name="register_passenger_for_ride"),
    path("for_ride/<uuid:ride_pk>", views.GetPassengersForRideGenericView.as_view(), name="get_passengers_for_ride"),
]
