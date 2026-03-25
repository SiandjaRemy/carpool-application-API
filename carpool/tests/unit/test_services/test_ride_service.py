import pytest
from datetime import timedelta
from django.utils import timezone
from carpool.services.ride_service import RideService
from carpool.enums.enums import (
    RequestStatus,
    ReservationPaymentStatus,
    ReservationStatus,
    RideStatus,
)
from carpool.tests.factories import (
    ReservationFactory,
    UserFactory,
    RideFactory,
    RideRequestFactory,
)

pytestmark = pytest.mark.unit


class TestRideService:
    """Unit tests for ride service"""

    # Create ride

    def test_create_ride_happy_path(self, db):
        """Test creating a ride successfully"""
        user = UserFactory()
        ride_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "departure_datetime": timezone.now() + timedelta(days=2),
            "available_seats": 4,
            "price_per_seat": 25.50,
        }

        ride = RideService.create_ride(ride_data, user)

        assert ride.id is not None
        assert ride.user == user
        assert ride.status == RideStatus.SCHEDULED
        assert ride.available_seats == 4

    def test_create_ride_fails_past_departure(self, db):
        """Test cannot create ride with past departure"""
        user = UserFactory()
        ride_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "departure_datetime": timezone.now() - timedelta(days=1),
            "available_seats": 4,
            "price_per_seat": 25.50,
        }

        with pytest.raises(ValueError, match="must be in the future"):
            RideService.create_ride(ride_data, user)

    # Update ride

    def test_update_ride_happy_path(self, db):
        """Test updating a ride"""
        user = UserFactory()
        ride = RideFactory(user=user, available_seats=4)

        update_data = {"available_seats": 3, "price_per_seat": 30.00}

        updated_ride = RideService.update_ride(update_data, ride, user)

        assert updated_ride.available_seats == 3
        assert updated_ride.price_per_seat == 30.00

    def test_update_ride_wrong_user(self, db):
        """Test cannot update another user's ride"""
        owner = UserFactory()
        wrong_user = UserFactory()
        ride = RideFactory(user=owner)

        data = {"available_seats": 3}
        with pytest.raises(ValueError, match="not found or you don't have permission"):
            RideService.update_ride(data, ride, wrong_user)

    # Cancel ride

    def test_cancel_ride_happy_path(self, db):
        """Test cancelling a ride"""
        user = UserFactory()
        ride = RideFactory(user=user, status=RideStatus.SCHEDULED)

        cancelled_ride = RideService.cancel_ride(ride.id, user)

        assert cancelled_ride.status == RideStatus.CANCELLED

    def test_cancel_ride_with_accepted_requests(self, db):
        """Test cancel ride with accepted requests and refund paid reservations"""
        user = UserFactory()
        ride = RideFactory(user=user)
        ride_request = RideRequestFactory(ride=ride, status=RequestStatus.ACCEPTED)

        ReservationFactory.from_request(ride_request)

        RideService.cancel_ride(ride.id, user)

        # The related requests will be set to cancelled by the user
        assert ride.requests.filter(status=RequestStatus.DRIVER_CANCELLED).exists()
        assert ride.reservations.filter(status=ReservationStatus.CANCELLED).exists()
        assert ride.reservations.filter(
            payment_status=ReservationPaymentStatus.PAYMENT_DISABLED
        ).exists()
