import pytest

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from carpool.enums.enums import ReservationPaymentStatus, ReservationStatus

pytestmark = pytest.mark.integration

departure_datetime = timezone.now() + timedelta(days=2)

base_ride_url = "carpool:rides-list"
base_ride_detail_url = "carpool:rides-detail"

ride_request_list_url = "carpool:requests-list"
ride_request_detail_url = "carpool:requests-detail"

ride_request_accept_url = "carpool:requests-accept"
ride_request_reject_url = "carpool:requests-reject"
ride_request_cancel_url = "carpool:requests-cancel"

ride_request_my_request_url = "carpool:requests-my-request"
ride_request_toggle_active_url = "carpool:requests-toggle-active"

# Reservations

reservations_list_url = "carpool:reservations-list"
reservations_detail_url = "carpool:reservations-detail"
reservation_payment_url = "carpool:reservations-payment"
reservation_cancel_url = "carpool:reservations-cancel"


@pytest.mark.django_db
class TestRefundBookingFlow:
    """Test refund booking flow from ride creation to refundment for paid reservation"""

    def test_happy_refund_flow(self, authenticated_client, passenger_client, db):
        """Test the entire happy booking process"""

        # 1. Driver creates a ride.
        # Our driver is authenticated_client

        ride_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "departure_datetime": (departure_datetime).isoformat(),
            "available_seats": 3,
            "price_per_seat": "25.00",
        }

        create_ride_response = authenticated_client.post(
            reverse(base_ride_url), ride_data
        )
        assert create_ride_response.status_code == status.HTTP_201_CREATED
        ride_id = create_ride_response.data["id"]

        # 2. Passenger requests to join
        # Our passenger is passenger_client

        request_data = {
            "seats_requested": 2,
            "price_per_seat": "25.00",
        }
        request_url = reverse(ride_request_list_url, kwargs={"rides_pk": ride_id})
        request_response = passenger_client.post(request_url, request_data)

        assert request_response.status_code == status.HTTP_201_CREATED
        request_id = request_response.data["id"]

        # 3. Driver accepts the request
        accept_url = reverse(
            ride_request_accept_url, kwargs={"rides_pk": ride_id, "pk": request_id}
        )
        accept_response = authenticated_client.patch(accept_url)

        assert accept_response.status_code == status.HTTP_200_OK

        # 4. Verify ride seats updated
        updated_ride_response = passenger_client.get(
            reverse(base_ride_detail_url, kwargs={"pk": ride_id})
        )
        assert updated_ride_response.data["available_seats"] == 1

        # 5. Passenger gets the list of his reservations
        # This is done so as to get the id of the reservation that will then be used in the payment url
        list_reservations_url = reverse(reservations_list_url)
        list_reservations_response = passenger_client.get(list_reservations_url)

        # 6. Check that the paginated response contains a ride
        assert list_reservations_response.data["count"] == 1

        # 7. More checks to ensure that the reservation is the one created when the request was accepted
        driver = authenticated_client.user
        passenger = passenger_client.user
        reservation_obj = list_reservations_response.data["results"][0]

        ride_str = f"{driver.email} will ride from {ride_data['departure_town']} to {ride_data['arrival_town']} on "
        # New reservations are pending
        assert reservation_obj["payment_status"] == ReservationPaymentStatus.PENDING
        assert reservation_obj["status"] == ReservationStatus.PENDING
        # Check the user and the str rep of the ride
        assert reservation_obj["passenger"]["id"] == str(passenger.id)
        assert ride_str in reservation_obj["ride"]

        # 8. Trigger payment for the ride
        # Note that payment_method is required
        payment_data = {"payment_method": "stripe"}
        payment_url = reverse(
            reservation_payment_url, kwargs={"pk": str(reservation_obj["id"])}
        )
        payment_response = passenger_client.patch(payment_url, payment_data)

        assert payment_response.status_code == status.HTTP_200_OK

        # 9. Check that the ride was updated
        detail_url = reverse(
            reservations_detail_url, kwargs={"pk": str(reservation_obj["id"])}
        )
        detail_response = passenger_client.get(detail_url)

        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.data["payment_status"] == ReservationPaymentStatus.PAID
        assert detail_response.data["status"] == ReservationStatus.CONFIRMED

        # 10. Trigger cancelation for this reservation
        # Cancelation for a paid reservation will update ReservationPaymentStatus from paid to refunded
        cancel_url = reverse(
            reservation_cancel_url, kwargs={"pk": str(reservation_obj["id"])}
        )
        cancel_response = passenger_client.patch(cancel_url)

        assert cancel_response.status_code == status.HTTP_200_OK

        # 11. Check that the ride was updated
        detail_url = reverse(
            reservations_detail_url, kwargs={"pk": str(reservation_obj["id"])}
        )
        detail_response = passenger_client.get(detail_url)

        assert detail_response.status_code == status.HTTP_200_OK
        assert (
            detail_response.data["payment_status"] == ReservationPaymentStatus.REFUNDED
        )
        assert detail_response.data["status"] == ReservationStatus.CANCELLED
