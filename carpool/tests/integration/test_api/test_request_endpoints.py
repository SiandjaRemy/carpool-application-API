import pytest

from django.urls import reverse
from rest_framework import status

from carpool.enums.enums import RequestStatus
from carpool.tests.factories import (
    UserFactory,
    RideFactory,
    RideRequestFactory,
)

pytestmark = pytest.mark.integration

base_url = "carpool:request-list"
base_detail_url = "carpool:request-detail"


class TestRideRequestEndpoints:
    """Test suite for ride request endpoints"""

    # ----------------------------------------------------------------------
    # List Requests (GET /rides/{ride_id}/requests/)
    # ----------------------------------------------------------------------

    def test_list_requests_for_ride_authenticated(self, authenticated_client, db):
        """Test authenticated user can list requests for a specific ride"""
        # Create a ride and some requests
        ride = RideFactory()
        request1 = RideRequestFactory(ride=ride)
        request2 = RideRequestFactory(ride=ride)

        url = reverse(base_url, kwargs={"rides_pk": ride.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_list_requests_for_ride_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot list requests"""
        ride = RideFactory()
        url = reverse(base_url, kwargs={"rides_pk": ride.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_requests_for_nonexistent_ride(self, authenticated_client, db):
        """Test listing requests for a ride that doesn't exist"""
        url = reverse(base_url, kwargs={"rides_pk": 99999})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ----------------------------------------------------------------------
    # Create Request (POST /rides/{ride_id}/requests/)
    # ----------------------------------------------------------------------

    def test_create_request_authenticated(self, authenticated_client, db):
        """Test authenticated user can create a ride request"""
        ride = RideFactory(available_seats=4)

        url = reverse(base_url, kwargs={"rides_pk": ride.id})
        data = {
            "seats_requested": 2,
            "price_per_seat": 25.30,
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["seats_requested"] == 2
        assert response.data["status"] == RequestStatus.PENDING
        assert response.data["ride"]["id"] == str(ride.id)
        assert response.data["passenger"]["id"] == str(authenticated_client.user.id)

    def test_create_request_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot create a request"""
        ride = RideFactory()

        url = reverse(base_url, kwargs={"rides_pk": ride.id})
        data = {
            "seats_requested": 3,
            "price_per_seat": 25.30,
        }

        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_request_exceeding_seats(self, authenticated_client, db):
        """Test creating request with more seats than available"""
        ride = RideFactory(available_seats=2)

        url = reverse(base_url, kwargs={"rides_pk": ride.id})
        data = {
            "seats_requested": 3,
            "price_per_seat": 25.30,
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "seats" in response.data["detail"].lower()

    def test_create_duplicate_request(self, authenticated_client, db):
        """Test user cannot create duplicate request for same ride"""
        ride = RideFactory(available_seats=4)
        user = authenticated_client.user

        # Create first request
        RideRequestFactory(ride=ride, passenger=user, seats_requested=1)

        # Try to create another
        url = reverse(base_url, kwargs={"rides_pk": ride.id})
        data = {"seats_requested": 2}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already" in response.data["detail"].lower()

    def test_create_request_for_own_ride(self, authenticated_client, db):
        """Test driver cannot request their own ride"""
        ride = RideFactory(driver=authenticated_client.user)

        url = reverse(base_url, kwargs={"rides_pk": ride.id})
        data = {"seats_requested": 1}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "a ride you created" in response.data["detail"].lower()

    def test_create_request_for_full_ride(self, authenticated_client, db):
        """Test creating request for a fully reserved ride"""
        # A full ride will not be found
        ride = RideFactory(available_seats=0)

        url = reverse(base_url, kwargs={"rides_pk": ride.id})
        data = {"seats_requested": 1}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.data["detail"].lower()

    # ----------------------------------------------------------------------
    # Retrieve Request (GET /rides/{ride_id}/requests/{request_id}/)
    # ----------------------------------------------------------------------

    def test_retrieve_request_authenticated(self, authenticated_client, db):
        """Test authenticated user can retrieve a specific request"""
        ride = RideFactory()
        ride_request = RideRequestFactory(ride=ride)

        url = reverse(
            base_detail_url, kwargs={"rides_pk": ride.id, "pk": ride_request.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(ride_request.id)
        assert response.data["seats_requested"] == ride_request.seats_requested

    def test_retrieve_request_different_user(
        self, authenticated_client, another_client, db
    ):
        """Test user cannot retrieve another user's request"""
        ride = RideFactory()
        other_user_request = RideRequestFactory(
            ride=ride, passenger=another_client.user
        )

        url = reverse(
            base_detail_url, kwargs={"rides_pk": ride.id, "pk": other_user_request.id}
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ----------------------------------------------------------------------
    # Update Request (PATCH /rides/{ride_id}/requests/{request_id}/)
    # ----------------------------------------------------------------------

    def test_update_request_seats(self, authenticated_client, db):
        """Test user can update their pending request"""
        ride = RideFactory(available_seats=5)
        ride_request = RideRequestFactory(
            ride=ride,
            passenger=authenticated_client.user,
            seats_requested=1,
            status="pending",
        )

        url = reverse(
            base_detail_url, kwargs={"rides_pk": ride.id, "pk": ride_request.id}
        )
        data = {"seats_requested": 2}
        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        ride_request.refresh_from_db()
        assert ride_request.seats_requested == 2

    def test_update_request_after_acceptance(self, authenticated_client, db):
        """Test user cannot update accepted request"""
        ride = RideFactory()
        ride_request = RideRequestFactory(
            ride=ride,
            passenger=authenticated_client.user,
            seats_requested=1,
            status=RequestStatus.ACCEPTED,
        )

        url = reverse(
            base_detail_url, kwargs={"rides_pk": ride.id, "pk": ride_request.id}
        )
        data = {"seats_requested": 2}
        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot be updated" in response.data["detail"].lower()

    # ----------------------------------------------------------------------
    # Custom Actions
    # ----------------------------------------------------------------------

    def test_accept_request_driver(self, authenticated_client, passenger_client, db):
        """Test user can accept a passenger's request"""
        ride = RideFactory(user=authenticated_client.user, available_seats=3)
        ride_request = RideRequestFactory(
            ride=ride,
            passenger=passenger_client.user,
            seats_requested=2,
        )

        url = reverse(
            "request-accept", kwargs={"rides_pk": ride.id, "pk": ride_request.id}
        )
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify request status updated
        ride_request.refresh_from_db()
        assert ride_request.status == RequestStatus.ACCEPTED

        # Verify ride seats decreased
        ride.refresh_from_db()
        assert ride.available_seats == 1

        # Verify reservation was created
        # assert hasattr(ride_request, "reservation")
        # assert ride_request.reservation is not None

    def test_accept_request_non_driver(
        self, authenticated_client, passenger_client, db
    ):
        """Test non-driver cannot accept a request"""
        ride = RideFactory(driver=UserFactory(), available_seats=3)
        ride_request = RideRequestFactory(
            ride=ride, passenger=passenger_client.user, seats_requested=2
        )

        url = reverse(
            "request-accept", kwargs={"rides_pk": ride.id, "pk": ride_request.id}
        )
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_accept_request_insufficient_seats(
        self, driver_client, passenger_client, db
    ):
        """Test driver cannot accept request if not enough seats"""
        ride = RideFactory(driver=driver_client.user, available_seats=1)
        ride_request = RideRequestFactory(
            ride=ride, passenger=passenger_client.user, seats_requested=2
        )

        url = reverse(
            "request-accept", kwargs={"rides_pk": ride.id, "pk": ride_request.id}
        )
        response = driver_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reject_request_driver(self, driver_client, passenger_client, db):
        """Test driver can reject a passenger's request"""
        ride = RideFactory(driver=driver_client.user)
        ride_request = RideRequestFactory(
            ride=ride, passenger=passenger_client.user, status="pending"
        )

        url = reverse(
            "request-reject", kwargs={"rides_pk": ride.id, "pk": ride_request.id}
        )
        response = driver_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        ride_request.refresh_from_db()
        assert ride_request.status == "rejected"

    def test_cancel_request_passenger(self, authenticated_client, db):
        """Test passenger can cancel their pending request"""
        ride = RideFactory()
        ride_request = RideRequestFactory(
            ride=ride, passenger=authenticated_client.user, status="pending"
        )

        url = reverse(
            "request-cancel", kwargs={"rides_pk": ride.id, "pk": ride_request.id}
        )
        response = authenticated_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        ride_request.refresh_from_db()
        assert ride_request.status == "cancelled"

    # ----------------------------------------------------------------------
    # My Requests Endpoint
    # ----------------------------------------------------------------------

    def test_my_requests_endpoint(self, authenticated_client, db):
        """Test user can list their own requests"""
        user = authenticated_client.user

        # Create requests for this user
        request1 = RideRequestFactory(passenger=user)
        request2 = RideRequestFactory(passenger=user)

        # Create request for another user (should not appear)
        RideRequestFactory()

        url = reverse("request-my-requests")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_my_requests_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot access my requests"""
        url = reverse("request-my-requests")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ----------------------------------------------------------------------
    # Toggle Active
    # ----------------------------------------------------------------------

    def test_toggle_request_active(self, authenticated_client, db):
        """Test user can toggle their request active status"""
        ride_request = RideRequestFactory(
            passenger=authenticated_client.user, is_active=True
        )

        url = reverse("request-toggle-active", kwargs={"pk": ride_request.id})
        response = authenticated_client.patch(url)

        assert response.status_code == status.HTTP_200_OK
        ride_request.refresh_from_db()
        assert ride_request.is_active is False

    def test_toggle_request_active_other_user(
        self, authenticated_client, another_client, db
    ):
        """Test user cannot toggle another user's request"""
        other_request = RideRequestFactory(passenger=another_client.user)

        url = reverse("request-toggle-active", kwargs={"pk": other_request.id})
        response = authenticated_client.patch(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
