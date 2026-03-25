from datetime import timedelta

import pytest

from django.utils import timezone

from carpool.enums.enums import RequestStatus
from carpool.services.request_service import RideRequestService
from carpool.tests.factories import RideFactory, RideRequestFactory, UserFactory

pytestmark = pytest.mark.unit


class TestRideRequestService:
    """Unit tests for ride request service"""

    # Testing Accept method

    def test_accept_request_happy_path(self, db):
        """Test the core business logic works"""
        # Setup
        driver = UserFactory()
        passenger = UserFactory()
        ride = RideFactory(user=driver, available_seats=3)
        ride_request = RideRequestFactory(
            ride=ride,
            passenger=passenger,
            seats_requested=2,
        )

        # Execute
        result = RideRequestService.accept_request(ride_request.id, driver)

        # Assert
        assert result.status == RequestStatus.ACCEPTED
        assert not result.is_active

        ride.refresh_from_db()
        assert ride.available_seats == 1

        # Verify reservation created
        assert ride.reservations.filter(passenger=passenger).exists()

    def test_accept_request_fails_for_wrong_user(self, db):
        """Test that non-owner cannot accept request"""
        driver = UserFactory()
        wrong_user = UserFactory()
        ride = RideFactory(user=driver)
        ride_request = RideRequestFactory(
            ride=ride,
        )

        with pytest.raises(ValueError, match="not found or you don't have permission"):
            RideRequestService.accept_request(ride_request.id, wrong_user)

    def test_accept_request_fails_if_not_pending(self, db):
        """Test that only pending requests can be accepted"""
        driver = UserFactory()
        ride = RideFactory(user=driver)
        ride_request = RideRequestFactory(
            ride=ride, status=RequestStatus.ACCEPTED  # Already accepted
        )

        with pytest.raises(ValueError, match="Only pending requests"):
            RideRequestService.accept_request(ride_request.id, driver)

    def test_accept_request_fails_if_insufficient_seats(self, db):
        """Test that request fails if not enough seats"""
        driver = UserFactory()
        passenger = UserFactory()
        ride = RideFactory(user=driver, available_seats=1)
        ride_request = RideRequestFactory(
            ride=ride,
            passenger=passenger,
            seats_requested=2,
        )

        with pytest.raises(ValueError, match="Not enough seats"):
            RideRequestService.accept_request(ride_request.id, driver)

    def test_accept_request_fails_if_ride_departed(self, db):
        """Test that request fails if ride has already departed"""
        # Use timezone.now() directly without freezer
        past_time = timezone.now() - timedelta(hours=2)

        driver = UserFactory()
        passenger = UserFactory()
        ride = RideFactory(user=driver, departure_datetime=past_time)
        ride_request = RideRequestFactory(
            ride=ride,
            passenger=passenger,
            seats_requested=1,
        )

        with pytest.raises(ValueError, match="already departed"):
            RideRequestService.accept_request(ride_request.id, driver)

    # Testing Reject method

    def test_reject_request_happy_path(self, db):
        """Test rejecting a request successfully"""
        driver = UserFactory()
        passenger = UserFactory()
        ride = RideFactory(user=driver)
        ride_request = RideRequestFactory(
            ride=ride,
            passenger=passenger,
        )

        result = RideRequestService.reject_request(ride_request.id, driver)

        assert result.status == RequestStatus.REJECTED
        assert not result.is_active

    # Testing Cancel method

    def test_cancel_request_happy_path(self, db):
        """Test passenger cancelling their request"""
        passenger = UserFactory()
        ride = RideFactory()
        ride_request = RideRequestFactory(
            ride=ride,
            passenger=passenger,
        )

        result = RideRequestService.cancel_request(ride_request.id, passenger)

        assert result.status == RequestStatus.CANCELLED
        assert not result.is_active
