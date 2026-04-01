import pytest

from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.cache import cache

from rest_framework import status
from carpool.tests.factories import RideFactory

from datetime import timedelta

pytestmark = pytest.mark.integration

ride_list_url = "v1:carpool:rides-list"
ride_cancel_url = "v1:carpool:rides-cancel"


@pytest.mark.django_db
class TestRideThrottling:

    def setup_method(self):
        """Clear cache before every test to reset throttle counters."""
        cache.clear()

    def get_unique_time(self, iteration):
        """Generate unique departure times for each iteration."""
        # Use iteration to space out rides by 3 hours to avoid conflicts
        return timezone.now() + timedelta(days=2, hours=iteration * 3)

    def test_list_rides_throttling(self, api_client):
        """Tests 'list' scope (50/hour)."""
        url = reverse(ride_list_url)

        # 1. Hit the limit (50)
        for _ in range(50):
            response = api_client.get(url)
            assert response.status_code == status.HTTP_200_OK

        # 2. The 51st request should be throttled
        response = api_client.get(url)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_create_ride_throttling(self, authenticated_client):
        """Tests 'user_create' scope (20/hour)."""
        url = reverse(ride_list_url)

        # 1. Use up the 20 allowed creations
        for i in range(20):
            payload = {
                "departure_town": f"London_{i}",
                "arrival_town": f"Manchester_{i}",
                "departure_datetime": self.get_unique_time(i).isoformat(),
                "available_seats": 3,
                "price_per_seat": 20.00,
            }
            response = authenticated_client.post(url, payload)
            assert response.status_code == status.HTTP_201_CREATED

        # 2. The 21st POST should fail
        response = authenticated_client.post(url, payload)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_cancel_ride_throttling(self, authenticated_client):
        """Tests 'user_custom' scope for the cancel action."""
        settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["user_custom"] = "2/hour"

        cache.clear()

        # Create 3 rides for 3 attempts
        rides = [RideFactory(user=authenticated_client.user) for _ in range(3)]

        # 1. Attempt 1 & 2: Should succeed (Rate is 2/hour)
        for i in range(2):
            url = reverse(ride_cancel_url, kwargs={"pk": rides[i].pk})
            response = authenticated_client.patch(url)
            assert response.status_code == status.HTTP_200_OK

        # 2. Attempt 3: MUST be 429
        url3 = reverse(ride_cancel_url, kwargs={"pk": rides[2].pk})
        response = authenticated_client.patch(url3)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "request was throttled" in response.data["detail"].lower()
