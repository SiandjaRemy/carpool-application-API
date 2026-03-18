import pytest

from datetime import timedelta

from rest_framework import status

from django.urls import reverse
from django.utils import timezone

from carpool.tests.factories import UserFactory, RideFactory

pytestmark = pytest.mark.integration


departure_datetime = timezone.now() + timedelta(days=1)

base_url = "v1:carpool:rides-list"
base_detail_url = "v1:carpool:rides-detail"


class TestRideEndpoints:

    def test_list_rides_authenticated(self, api_client, db):
        """Test authenticated user can list rides"""
        # Create test data
        user = UserFactory()
        api_client.force_authenticate(user=user)
        RideFactory.create_batch(3)

        url = reverse(base_url)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3

    def test_list_rides_unauthenticated(self, api_client, db):
        """Test unauthenticated user can list rides (public endpoint)"""
        RideFactory.create_batch(2)

        url = reverse(base_url)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    def test_create_ride_authenticated(self, api_client, db):
        """Test authenticated user can create a ride"""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        url = reverse(base_url)
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "departure_datetime": (departure_datetime).isoformat(),
            "available_seats": 3,
            "price_per_seat": "30.00",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["user"]["id"] == str(user.id)

    # def test_filter_rides_by_location(self, api_client, db):
    #     """Test filtering rides by departure_town/arrival_town"""
    #     user = UserFactory()
    #     api_client.force_authenticate(user=user)

    #     RideFactory(departure_town="New York", arrival_town="Boston")
    #     RideFactory(departure_town="New York", arrival_town="Philadelphia")
    #     RideFactory(departure_town="Boston", arrival_town="New York")

    #     url = reverse(base_url)
    #     response = api_client.get(url, {"departure_town": "New York"})

    #     assert response.status_code == status.HTTP_200_OK
    #     assert response.data["count"] == 2
