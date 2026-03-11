import pytest
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from carpool.enums.enums import RideStatus
from carpool.models import Ride
from carpool.tests.factories import (
    FullyReservedRideFactory,
    RideFactory,
    UserFactory,
)

pytestmark = pytest.mark.unit


departure_datetime = timezone.now() + timedelta(days=1)


class TestRideModel:

    def test_create_ride(self, db):
        """Test creating a ride with valid data"""
        user = UserFactory()

        ride = Ride.objects.create(
            user=user,
            departure_town="Paris",
            arrival_town="Lyon",
            departure_datetime=departure_datetime,
            available_seats=5,
            price_per_seat=30.45,  # Lets assume it's in euros
        )

        assert ride.id is not None
        assert ride.status == RideStatus.SHECDULED
        assert not ride.fully_reserved

    def test_ride_factory_creates_valid_ride(self, db):
        """Test ride factory creates valid objects"""
        ride = RideFactory()

        assert ride.id is not None
        assert ride.status == RideStatus.SHECDULED
        assert ride.available_seats >= 1
        assert ride.available_seats <= 10
        assert ride.price_per_seat == 25.50

    def test_seats_available_property(self, db):
        """Test seats_available property returns correct value"""
        ride_with_seats = RideFactory()
        assert ride_with_seats.seats_available

        fully_reserved_ride = FullyReservedRideFactory()
        assert not fully_reserved_ride.seats_available

    def test_available_seats_validation(self, db):
        """Test available_seats field validation"""
        user = UserFactory()

        # Test minimum seats
        with pytest.raises(ValidationError):
            ride = Ride.objects.create(
                user=user,
                departure_town="Paris",
                arrival_town="Lyon",
                departure_datetime=departure_datetime,
                available_seats=0,  # Invalid
                price_per_seat=30.45,  # Lets assume it's in euros
            )
            ride.full_clean()

        # Test maximum seats
        with pytest.raises(ValidationError):
            ride = Ride.objects.create(
                user=user,
                departure_town="Paris",
                arrival_town="Lyon",
                departure_datetime=departure_datetime,
                available_seats=11,  # Invalid
                price_per_seat=30.45,  # Lets assume it's in euros
            )
            ride.full_clean()

    def test_price_per_seat_positive(self, db):
        """Test price_per_seat must be positive"""
        user = UserFactory()

        with pytest.raises(ValidationError):
            ride = Ride.objects.create(
                user=user,
                departure_town="Paris",
                arrival_town="Lyon",
                departure_datetime=departure_datetime,
                available_seats=7,
                price_per_seat=30.45,  # Invalid
            )
            ride.full_clean()
