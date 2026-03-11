import pytest

from django.core.exceptions import ValidationError

from carpool.enums.enums import RequestStatus
from carpool.models import RideRequest
from carpool.tests.factories import RideFactory, RideRequestFactory, UserFactory


pytestmark = pytest.mark.unit


class TestRideRequestModel:

    def test_create_ride_request(self, db):
        """Test creating a ride request with valid data"""
        ride = RideFactory()
        passenger = UserFactory()

        ride_request = RideRequest.objects.create(
            ride=ride,
            passenger=passenger,
            seats_requested=2,
            price_per_seat=25.50,
        )

        assert ride_request.id is not None
        assert ride_request.status == RequestStatus.PENDING
        assert ride_request.seats_requested == 2
        assert ride_request.is_active

    def test_ride_request_factory_creates_valid_ride_request(self, db):
        """Test ride request factory creates valid objects"""
        ride_request = RideRequestFactory()

        assert ride_request.id is not None
        assert ride_request.status == RequestStatus.PENDING
        assert ride_request.seats_requested >= 1
        assert ride_request.seats_requested <= 10
        assert ride_request.price_per_seat == 25.50

    def test_seats_requested_validation(self, db):
        """Test seats_requested field validation"""
        ride = RideFactory()
        passenger = UserFactory()

        # Test minimum seats
        with pytest.raises(ValidationError):
            ride_request = RideRequest(
                ride=ride,
                passenger=passenger,
                seats_requested=0,  # Invalid
                price_per_seat=25.50,
            )
            ride_request.full_clean()

        # Test maximum seats
        with pytest.raises(ValidationError):
            ride_request = RideRequest(
                ride=ride,
                passenger=passenger,
                seats_requested=11,  # Invalid
                price_per_seat=25.50,
            )
            ride_request.full_clean()

    def test_price_per_seat_positive(self, db):
        """Test price_per_seat must be positive"""
        ride = RideFactory()
        passenger = UserFactory()

        with pytest.raises(ValidationError):
            ride_request = RideRequest(
                ride=ride,
                passenger=passenger,
                seats_requested=2,
                price_per_seat=-10.0,  # Invalid
            )
            ride_request.full_clean()
