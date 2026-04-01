import pytest
from django.urls import reverse
from rest_framework import status

from carpool.enums.enums import ReservationPaymentStatus, ReservationStatus
from carpool.tests.factories import (
    RideFactory,
    ReservationFactory,
)

pytestmark = pytest.mark.integration

# URL names
reservation_list_url = "v1:carpool:reservations-list"
reservation_detail_url = "v1:carpool:reservations-detail"
reservation_cancel_url = "v1:carpool:reservations-cancel"
reservation_payment_url = "v1:carpool:reservations-payment"


@pytest.mark.django_db
class TestReservationEndpoints:
    """Test suite for reservation endpoints"""

    # ----------------------------------------------------------------------
    # List Reservations (GET /reservations/)
    # ----------------------------------------------------------------------

    def test_list_own_reservations_authenticated(self, authenticated_client, db):
        """Test authenticated user can list their own reservations"""
        user = authenticated_client.user

        # Create reservations for this user
        ReservationFactory(passenger=user)
        ReservationFactory(passenger=user)

        # Create reservation for another user (should not appear)
        ReservationFactory()

        url = reverse(reservation_list_url)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

        # Verify the reservations belong to the user
        for result in response.data["results"]:
            assert result["passenger"]["id"] == str(user.id)

    def test_list_reservations_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot list reservations"""
        url = reverse(reservation_list_url)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_reservations_empty_for_new_user(self, authenticated_client, db):
        """Test new user sees empty reservation list"""
        url = reverse(reservation_list_url)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    # ----------------------------------------------------------------------
    # Retrieve Reservation (GET /reservations/{id}/)
    # ----------------------------------------------------------------------

    def test_retrieve_own_reservation(self, authenticated_client, db):
        """Test user can retrieve their own reservation"""
        user = authenticated_client.user
        reservation = ReservationFactory(passenger=user)

        url = reverse(reservation_detail_url, kwargs={"pk": reservation.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(reservation.id)
        assert response.data["passenger"]["id"] == str(user.id)
        assert response.data["seats_requested"] == reservation.seats_requested

    def test_retrieve_others_reservation(
        self, authenticated_client, another_client, db
    ):
        """Test user cannot retrieve another user's reservation"""
        other_reservation = ReservationFactory(passenger=another_client.user)

        url = reverse(reservation_detail_url, kwargs={"pk": other_reservation.id})
        response = authenticated_client.get(url)

        # Should return 404 for security (doesn't reveal existence)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_reservation_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot retrieve reservation"""
        reservation = ReservationFactory()

        url = reverse(reservation_detail_url, kwargs={"pk": reservation.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_nonexistent_reservation(self, authenticated_client, db):
        """Test retrieving a reservation that doesn't exist"""
        url = reverse(
            reservation_detail_url,
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ----------------------------------------------------------------------
    # Create Reservation - Should be disabled
    # ----------------------------------------------------------------------

    def test_create_reservation_disabled(self, authenticated_client, db):
        """Test that creating reservations directly is not allowed"""
        ride = RideFactory()

        url = reverse(reservation_list_url)
        data = {
            "ride_id": str(ride.id),
            "seats_requested": 2,
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    # ----------------------------------------------------------------------
    # Update Reservation - Should be disabled (except custom action)
    # ----------------------------------------------------------------------

    def test_update_reservation_disabled(self, authenticated_client, db):
        """Test that updating reservations directly is not allowed"""
        user = authenticated_client.user
        reservation = ReservationFactory(passenger=user)

        url = reverse(reservation_detail_url, kwargs={"pk": reservation.id})
        data = {"seats_requested": 3}

        # Test PUT
        put_response = authenticated_client.put(url, data, format="json")
        assert put_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Test PATCH (without using cancel action)
        patch_response = authenticated_client.patch(url, data, format="json")
        assert patch_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_reservation_disabled(self, authenticated_client, db):
        """Test that deleting reservations directly is not allowed"""
        user = authenticated_client.user
        reservation = ReservationFactory(passenger=user)

        url = reverse(reservation_detail_url, kwargs={"pk": reservation.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    # ----------------------------------------------------------------------
    # Cancel Reservation Action (PATCH /reservations/{id}/cancel/)
    # ----------------------------------------------------------------------

    def test_cancel_own_pending_reservation(self, authenticated_client, db, freezer):
        """Test user can cancel their own pending reservation even 1 hour before departure"""
        from django.utils import timezone
        from datetime import timedelta

        user = authenticated_client.user
        now = timezone.now()
        freezer.move_to(now)

        # Create a ride departing in 1 hours
        # 8 seats only so that cancel will make limit to exceeded
        ride = RideFactory(
            departure_datetime=now + timedelta(hours=1), available_seats=8
        )
        # Create a paid reservation for that ride
        reservation = ReservationFactory(
            passenger=user,
            ride=ride,
            seats_requested=2,
        )

        # Record initial seat count
        initial_seats = ride.available_seats

        url = reverse(reservation_cancel_url, kwargs={"pk": reservation.id})
        response = authenticated_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Reservation cancelled successfully"

        # Verify reservation was updated
        reservation.refresh_from_db()
        assert reservation.status == ReservationStatus.CANCELLED
        # Since no payment was made, disable instead of refunding
        assert reservation.payment_status == ReservationPaymentStatus.PAYMENT_DISABLED

        # Verify seats were returned to the ride
        ride.refresh_from_db()
        assert ride.available_seats == initial_seats + 2

    def test_cancel_own_reservation(self, authenticated_client, db, freezer):
        """Test user cant cancel their paid reservation 2 hour before departure"""
        from django.utils import timezone
        from datetime import timedelta

        user = authenticated_client.user
        now = timezone.now()
        freezer.move_to(now)

        # Create a ride departing in 2 hours
        ride = RideFactory(
            departure_datetime=now + timedelta(hours=2), available_seats=8
        )
        # Create a paid reservation for that ride
        reservation = ReservationFactory(
            passenger=user,
            ride=ride,
            seats_requested=2,
            payment_status=ReservationPaymentStatus.PAID,
            status=ReservationStatus.CONFIRMED,
        )

        # Record initial seat count
        initial_seats = ride.available_seats

        url = reverse(reservation_cancel_url, kwargs={"pk": reservation.id})
        response = authenticated_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            "cannot cancel paid reservation less than 2 hours before departure"
            in response.data["detail"].lower()
        )

        # Verify reservation was updated
        reservation.refresh_from_db()
        assert reservation.status == ReservationStatus.CONFIRMED
        assert reservation.payment_status == ReservationPaymentStatus.PAID

        # Verify seats were returned to the ride
        ride.refresh_from_db()
        assert ride.available_seats == initial_seats

    def test_cancel_others_reservation(
        self, authenticated_client, another_client, db, freezer
    ):
        """Test user cannot cancel another user's reservation"""
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        freezer.move_to(now)

        ride = RideFactory(departure_datetime=now + timedelta(hours=3))
        other_reservation = ReservationFactory(passenger=another_client.user, ride=ride)

        url = reverse(reservation_cancel_url, kwargs={"pk": other_reservation.id})
        response = authenticated_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cancel_reservation_late(self, authenticated_client, db, freezer):
        """Test user can cancel pending reservation close to departure"""
        from django.utils import timezone
        from datetime import timedelta

        user = authenticated_client.user
        now = timezone.now()
        freezer.move_to(now)

        # Create ride departing in 1 hour (less than 2-hour window)
        ride = RideFactory(
            departure_datetime=now + timedelta(hours=1), available_seats=5
        )
        reservation = ReservationFactory(passenger=user, ride=ride, seats_requested=4)

        url = reverse(reservation_cancel_url, kwargs={"pk": reservation.id})
        response = authenticated_client.patch(url, {}, format="json")

        print("###################################")
        print(f"Response: {response.data}")
        assert response.status_code == status.HTTP_200_OK

    def test_cancel_already_cancelled_reservation(
        self, authenticated_client, db, freezer
    ):
        """Test user cannot cancel an already cancelled reservation"""
        from django.utils import timezone
        from datetime import timedelta

        user = authenticated_client.user
        now = timezone.now()
        freezer.move_to(now)

        ride = RideFactory(departure_datetime=now + timedelta(hours=3))
        reservation = ReservationFactory(
            passenger=user, ride=ride, status=ReservationStatus.CANCELLED
        )

        url = reverse(reservation_cancel_url, kwargs={"pk": reservation.id})
        response = authenticated_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already cancelled" in response.data["detail"].lower()

    def test_cancel_reservation_ride_departed(self, authenticated_client, db, freezer):
        """Test user cannot cancel reservation for departed ride"""
        from django.utils import timezone
        from datetime import timedelta

        user = authenticated_client.user
        now = timezone.now()
        freezer.move_to(now)

        # Ride that departed 1 hour ago
        ride = RideFactory(departure_datetime=now - timedelta(hours=1))
        reservation = ReservationFactory(passenger=user, ride=ride)

        url = reverse(reservation_cancel_url, kwargs={"pk": reservation.id})
        response = authenticated_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cancelled automatically" in response.data["detail"].lower()

    def test_cancel_nonexistent_reservation(self, authenticated_client, db):
        """Test cancelling a reservation that doesn't exist"""
        url = reverse(
            reservation_cancel_url,
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )

        response = authenticated_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_reservation_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot cancel reservation"""
        reservation = ReservationFactory()

        url = reverse(reservation_cancel_url, kwargs={"pk": reservation.id})
        response = api_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ----------------------------------------------------------------------
    # Cancel Reservation Action (PATCH /reservations/{id}/cancel/)
    # ----------------------------------------------------------------------

    def test_pay_own_reservation(self, authenticated_client, db):
        """Test user can pay for their own reservation"""

        user = authenticated_client.user

        # Create a ride departing in 3 hours
        ride = RideFactory()
        reservation = ReservationFactory(
            passenger=user,
            ride=ride,
            seats_requested=2,
        )

        url = reverse(reservation_payment_url, kwargs={"pk": reservation.id})
        data = {"payment_method": "stripe"}

        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["reservation_status"] == ReservationStatus.CONFIRMED
        assert response.data["detail"] == "Payment completed"

    def test_pay_reservation_needs_payment_method(self, authenticated_client, db):
        """Test that a payment method needs to be passed for payment to be processed"""

        user = authenticated_client.user

        # Create a ride departing in 3 hours
        ride = RideFactory()
        reservation = ReservationFactory(
            passenger=user,
            ride=ride,
            seats_requested=2,
        )

        url = reverse(reservation_payment_url, kwargs={"pk": reservation.id})
        data = {}

        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "payment_method" in response.data

    def test_pay_others_reservation(self, authenticated_client, another_client, db):
        """Test user cannot pay for another user's reservation"""

        other_reservation = ReservationFactory(passenger=another_client.user)

        url = reverse(reservation_payment_url, kwargs={"pk": other_reservation.id})
        data = {"payment_method": "stripe"}

        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_pay_reservation_late(self, authenticated_client, db, freezer):
        """Test user can pay for reservation even close to departure"""
        from django.utils import timezone
        from datetime import timedelta

        user = authenticated_client.user
        now = timezone.now()
        freezer.move_to(now)

        # Create ride departing in 1 hour (less than 2-hour window)
        ride = RideFactory(departure_datetime=now + timedelta(hours=1))
        reservation = ReservationFactory(passenger=user, ride=ride)

        url = reverse(reservation_payment_url, kwargs={"pk": reservation.id})
        data = {"payment_method": "stripe"}

        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

    def test_pay_already_processed_reservation(self, authenticated_client, db, freezer):
        """Test user cannot pay for an already cancelled/confirmed reservation"""
        user = authenticated_client.user

        cancelled_reservation = ReservationFactory(
            passenger=user, status=ReservationStatus.CANCELLED
        )
        confirmed_reservation = ReservationFactory(
            passenger=user, status=ReservationStatus.CONFIRMED
        )

        # URLs
        cancelled_reservation_url = reverse(
            reservation_payment_url, kwargs={"pk": cancelled_reservation.id}
        )
        confirmed_reservation_url = reverse(
            reservation_payment_url, kwargs={"pk": confirmed_reservation.id}
        )
        data = {"payment_method": "stripe"}

        # Requests
        cancelled_response = authenticated_client.patch(
            cancelled_reservation_url, data, format="json"
        )
        confirmed_response = authenticated_client.patch(
            confirmed_reservation_url, data, format="json"
        )

        # Assrtions
        assert cancelled_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cancelled reservations" in cancelled_response.data["detail"].lower()

        assert confirmed_response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already paid" in confirmed_response.data["detail"].lower()

    def test_pay_reservation_ride_departed(self, authenticated_client, db, freezer):
        """Test user cannot pay for a reservation for departed ride"""
        from django.utils import timezone
        from datetime import timedelta

        user = authenticated_client.user
        now = timezone.now()
        freezer.move_to(now)

        # Ride that departed 1 hour ago
        ride = RideFactory(departure_datetime=now - timedelta(hours=1))
        reservation = ReservationFactory(passenger=user, ride=ride)

        url = reverse(reservation_payment_url, kwargs={"pk": reservation.id})
        data = {"payment_method": "stripe"}

        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "too late" in response.data["detail"].lower()

    def test_pay_nonexistent_reservation(self, authenticated_client, db):
        """Test payment for a reservation that doesn't exist"""
        url = reverse(
            reservation_payment_url,
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )

        response = authenticated_client.patch(url, {}, format="json")

        # assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_pay_reservation_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot pay for reservation"""
        reservation = ReservationFactory()

        url = reverse(reservation_payment_url, kwargs={"pk": reservation.id})
        response = api_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # ----------------------------------------------------------------------
    # Filtering and Pagination Tests
    # ----------------------------------------------------------------------

    def test_reservations_pagination(self, authenticated_client, db):
        """Test that reservations are paginated correctly"""
        user = authenticated_client.user

        # Create 15 reservations (more than default page size)
        for i in range(15):
            ReservationFactory(passenger=user)

        url = reverse(reservation_list_url)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert response.data["count"] == 15
        assert "next" in response.data
        assert "previous" in response.data
        assert len(response.data["results"]) == 10  # Default page size

    def test_reservations_ordered_by_created_at(
        self, authenticated_client, db, freezer
    ):
        """Test that reservations are ordered by created_at descending"""
        from django.utils import timezone
        from datetime import timedelta

        user = authenticated_client.user
        now = timezone.now()

        # Freeze time at different points
        freezer.move_to(now - timedelta(days=5))
        old = ReservationFactory(passenger=user)

        freezer.move_to(now - timedelta(days=2))
        middle = ReservationFactory(passenger=user)

        freezer.move_to(now)
        recent = ReservationFactory(passenger=user)

        url = reverse(reservation_list_url)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        results = response.data["results"]
        assert results[0]["id"] == str(recent.id)
        assert results[1]["id"] == str(middle.id)
        assert results[2]["id"] == str(old.id)
