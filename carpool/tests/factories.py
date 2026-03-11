import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from carpool.enums.enums import RequestStatus, ReservationPaymentStatus, RideStatus
from carpool.models import Ride, RideRequest, RideAlert, Reservation
from datetime import datetime, timedelta

User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True


#########################################################################


class RideFactory(DjangoModelFactory):
    class Meta:
        model = Ride

    user = factory.SubFactory(UserFactory)
    departure_town = factory.Faker("city")
    arrival_town = factory.Faker("city")
    departure_datetime = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=1)
    )
    available_seats = 10
    price_per_seat = 25.50
    status = RideStatus.SHECDULED


class FullyReservedRideFactory(RideFactory):
    """Factory for total ride reservations"""

    available_seats = 0
    fully_reserved = True


#########################################################################


class RideRequestFactory(DjangoModelFactory):
    class Meta:
        model = RideRequest

    ride = factory.SubFactory(RideFactory)
    passenger = factory.SubFactory(UserFactory)
    seats_requested = factory.Faker("random_int", min=1, max=10)
    price_per_seat = 25.50
    status = RequestStatus.PENDING


#########################################################################


class ReservationFactory(DjangoModelFactory):
    class Meta:
        model = Reservation

    ride = factory.SubFactory(RideFactory)
    passenger = factory.SubFactory(UserFactory)
    seats_requested = factory.Faker("random_int", min=1, max=10)
    price_per_seat = 25.50
    payment_status = ReservationPaymentStatus.PENDING

    @classmethod
    def from_request(cls, ride_request: RideRequest):
        """Factory method to create reservation from a ride request"""
        return cls(
            ride=ride_request.ride,
            passenger=ride_request.passenger,
            seats_requested=ride_request.seats_requested,
            price_per_seat=ride_request.ride.price_per_seat,
        )


class ConfirmedReservationFactory(ReservationFactory):
    """Factory for confirmed reservations"""

    payment_status = ReservationPaymentStatus.CONFIRMED
    confirmed_at = factory.LazyFunction(lambda: datetime.now())


class FailedReservationFactory(ReservationFactory):
    """Factory for failed payment reservations"""

    payment_status = ReservationPaymentStatus.FAILED
    confirmed_at = None


#########################################################################


class RideAlertFactory(DjangoModelFactory):
    class Meta:
        model = RideAlert

    user = factory.SubFactory(UserFactory)
    origin = factory.Faker("city")
    destination = factory.Faker("city")
    date_from = factory.LazyFunction(lambda: datetime.now().date())
    date_to = factory.LazyFunction(lambda: datetime.now().date() + timedelta(days=7))
    is_active = True
