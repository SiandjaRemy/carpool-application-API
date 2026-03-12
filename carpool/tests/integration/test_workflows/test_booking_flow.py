import pytest

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from carpool.tests.factories import UserFactory
from carpool.models import Reservation

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


class TestCompleteBookingFlow:
    """Test complete booking flow from ride creation to reservation"""

    def test_complete_booking_flow(self, api_client, db):
        """Test the entire booking process"""

        # 1. Driver creates a ride
        driver = UserFactory()
        api_client.force_authenticate(user=driver)

        ride_data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "departure_datetime": (departure_datetime).isoformat(),
            "available_seats": 3,
            "price_per_seat": "25.00",
        }

        create_ride_response = api_client.post(reverse(base_ride_url), ride_data)
        assert create_ride_response.status_code == status.HTTP_201_CREATED
        ride_id = create_ride_response.data["id"]

        # 2. Passenger requests to join
        passenger = UserFactory()
        api_client.force_authenticate(user=passenger)

        request_data = {
            "seats_requested": 2,
            "price_per_seat": "25.00",
        }
        request_url = reverse(ride_request_list_url, kwargs={"rides_pk": ride_id})
        request_response = api_client.post(request_url, request_data)

        assert request_response.status_code == status.HTTP_201_CREATED
        request_id = request_response.data["id"]

        # 3. Driver accepts the request
        api_client.force_authenticate(user=driver)
        accept_url = reverse(
            ride_request_accept_url, kwargs={"rides_pk": ride_id, "pk": request_id}
        )
        accept_response = api_client.post(accept_url)

        assert accept_response.status_code == status.HTTP_200_OK

        # 4. Verify reservation was created
        assert Reservation.objects.filter(ride_id=ride_id).exists()

        # 5. Verify ride seats updated
        updated_ride_response = api_client.get(
            reverse(base_ride_detail_url, kwargs={"pk": ride_id})
        )
        assert updated_ride_response.data["available_seats"] == 1
