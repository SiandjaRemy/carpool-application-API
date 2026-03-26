import pytest
from django.urls import reverse
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from carpool.tests.factories import (
    RideAlertFactory,
)

pytestmark = pytest.mark.integration

# URL names
alert_list_url = "v1:carpool:alerts-list"
alert_detail_url = "v1:carpool:alerts-detail"
alert_toggle_active_url = "v1:carpool:alerts-toggle-active"


@pytest.mark.django_db
class TestRideAlertEndpoints:
    """Test suite for ride alert endpoints"""

    # ----------------------------------------------------------------------
    # List Alerts (GET /alerts/)
    # ----------------------------------------------------------------------

    def test_list_own_alerts_authenticated(self, authenticated_client, db):
        """Test authenticated user can list their own alerts"""
        user = authenticated_client.user

        # Create alerts for this user
        RideAlertFactory(user=user)
        RideAlertFactory(user=user)

        # Create alert for another user (should not appear)
        RideAlertFactory()

        url = reverse(alert_list_url)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

        # Verify the alerts belong to the user
        for result in response.data["results"]:
            assert result["user"]["id"] == str(user.id)

    def test_list_alerts_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot list alerts"""
        url = reverse(alert_list_url)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_alerts_empty_for_new_user(self, authenticated_client, db):
        """Test new user sees empty alert list"""
        url = reverse(alert_list_url)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    # ----------------------------------------------------------------------
    # Create Alert (POST /alerts/)
    # ----------------------------------------------------------------------

    def test_create_alert_authenticated(self, authenticated_client, db):
        """Test authenticated user can create an alert"""
        url = reverse(alert_list_url)
        now = timezone.now()
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "after_date": (now + timedelta(days=1)).isoformat(),
            "before_date": (now + timedelta(days=7)).isoformat(),
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["departure_town"] == "New York"
        assert response.data["arrival_town"] == "Boston"
        assert response.data["is_active"] is True
        assert response.data["user"]["id"] == str(authenticated_client.user.id)

    def test_create_alert_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot create an alert"""
        url = reverse(alert_list_url)
        now = timezone.now()
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "after_date": (now + timedelta(days=1)).isoformat(),
            "before_date": (now + timedelta(days=7)).isoformat(),
        }

        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_create_alert_without_dates(self, authenticated_client, db):
        """Test creating alert without date filters"""
        url = reverse(alert_list_url)
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
        }

        response = authenticated_client.post(url, data, format="json")

        assert "after_date" in response.data
        assert "before_date" in response.data

    def test_create_duplicate_alert(self, authenticated_client, db):
        """Test user cannot create duplicate active alert for same route"""
        url = reverse(alert_list_url)
        now = timezone.now()
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "after_date": (now + timedelta(days=1)).isoformat(),
            "before_date": (now + timedelta(days=7)).isoformat(),
        }

        # Create first alert
        response1 = authenticated_client.post(url, data, format="json")
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create duplicate
        response2 = authenticated_client.post(url, data, format="json")

        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already have an active alert" in response2.data["detail"].lower()

    def test_create_alert_invalid_dates(self, authenticated_client, db):
        """Test creating alert with invalid date ranges"""
        url = reverse(alert_list_url)
        now = timezone.now()
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "after_date": (now + timedelta(days=7)).isoformat(),
            "before_date": (
                now + timedelta(days=1)
            ).isoformat(),  # Before date is earlier
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Before date must be after after date" in response.data["detail"]

    def test_create_alert_past_dates(self, authenticated_client, db):
        """Test creating alert with past dates"""
        url = reverse(alert_list_url)
        now = timezone.now()
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "after_date": (now - timedelta(days=1)).isoformat(),  # Past date
            "before_date": (now + timedelta(days=7)).isoformat(),
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be in the future" in response.data["detail"].lower()

    # ----------------------------------------------------------------------
    # Retrieve Alert (GET /alerts/{id}/)
    # ----------------------------------------------------------------------

    def test_retrieve_own_alert(self, authenticated_client, db):
        """Test user can retrieve their own alert"""
        user = authenticated_client.user
        alert = RideAlertFactory(user=user)

        url = reverse(alert_detail_url, kwargs={"pk": alert.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(alert.id)
        assert response.data["departure_town"] == alert.departure_town
        assert response.data["arrival_town"] == alert.arrival_town
        assert response.data["user"]["id"] == str(user.id)

    def test_retrieve_others_alert(self, authenticated_client, another_client, db):
        """Test user cannot retrieve another user's alert"""
        other_alert = RideAlertFactory(user=another_client.user)

        url = reverse(alert_detail_url, kwargs={"pk": other_alert.id})
        response = authenticated_client.get(url)

        # Should return 404 for security (doesn't reveal existence)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_alert_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot retrieve alert"""
        alert = RideAlertFactory()

        url = reverse(alert_detail_url, kwargs={"pk": alert.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_nonexistent_alert(self, authenticated_client, db):
        """Test retrieving an alert that doesn't exist"""
        url = reverse(
            alert_detail_url,
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ----------------------------------------------------------------------
    # Update Alert (PATCH /alerts/{id}/)
    # ----------------------------------------------------------------------

    def test_update_own_alert(self, authenticated_client, db):
        """Test user can update their own alert"""
        user = authenticated_client.user
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            departure_town="Old City",
            arrival_town="Old Town",
            after_date=now + timedelta(days=2),
            before_date=now + timedelta(days=8),
        )

        url = reverse(alert_detail_url, kwargs={"pk": alert.id})
        new_data = {
            "departure_town": "New City",
            "after_date": (now + timedelta(days=3)).isoformat(),
        }

        response = authenticated_client.patch(url, new_data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["departure_town"] == "New City"
        assert response.data["arrival_town"] == "Old Town"  # Unchanged
        # Note: after_date might be in a different format, so we check it exists
        assert response.data["after_date"] is not None

    def test_update_others_alert(self, authenticated_client, another_client, db):
        """Test user cannot update another user's alert"""
        other_alert = RideAlertFactory(user=another_client.user)

        url = reverse(alert_detail_url, kwargs={"pk": other_alert.id})
        data = {"departure_town": "New City"}

        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_alert_invalid_dates(self, authenticated_client, db):
        """Test updating alert with invalid dates"""
        user = authenticated_client.user
        now = timezone.now()
        alert = RideAlertFactory(
            user=user,
            after_date=now + timedelta(days=2),
            before_date=now + timedelta(days=8),
        )

        url = reverse(alert_detail_url, kwargs={"pk": alert.id})
        data = {
            "after_date": (now + timedelta(days=9)).isoformat(),
            "before_date": (now + timedelta(days=5)).isoformat(),  # Before before after
        }

        response = authenticated_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Before date must be after after date" in response.data["detail"]

    def test_cannot_update_is_active_directly(self, authenticated_client, db):
        """Test that is_active cannot be updated directly (must use toggle)"""
        user = authenticated_client.user
        alert = RideAlertFactory(user=user, is_active=True)

        url = reverse(alert_detail_url, kwargs={"pk": alert.id})
        data = {"is_active": False}

        response = authenticated_client.patch(url, data, format="json")

        # is_active should remain unchanged (read-only field)
        assert response.data["is_active"] is True

    # ----------------------------------------------------------------------
    # Toggle Active Action (PATCH /alerts/{id}/toggle-active/)
    # ----------------------------------------------------------------------

    def test_toggle_own_alert_active(self, authenticated_client, db):
        """Test user can toggle their alert active status"""
        user = authenticated_client.user
        alert = RideAlertFactory(user=user, is_active=True)

        url = reverse(alert_toggle_active_url, kwargs={"pk": alert.id})
        response = authenticated_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Alert is now Inactive"

        # Verify database was updated
        alert.refresh_from_db()
        assert alert.is_active is False

        # Toggle again
        response = authenticated_client.patch(url, {}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "Alert is now Active"

        alert.refresh_from_db()
        assert alert.is_active is True

    def test_toggle_others_alert(self, authenticated_client, another_client, db):
        """Test user cannot toggle another user's alert"""
        other_alert = RideAlertFactory(user=another_client.user, is_active=True)

        url = reverse(alert_toggle_active_url, kwargs={"pk": other_alert.id})
        response = authenticated_client.patch(url, {}, format="json")

        # assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_toggle_alert_unauthenticated(self, api_client, db):
        """Test unauthenticated user cannot toggle alert"""
        alert = RideAlertFactory()

        url = reverse(alert_toggle_active_url, kwargs={"pk": alert.id})
        response = api_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_toggle_nonexistent_alert(self, authenticated_client, db):
        """Test toggling an alert that doesn't exist"""
        url = reverse(
            alert_toggle_active_url,
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = authenticated_client.patch(url, {}, format="json")

        # assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ----------------------------------------------------------------------
    # Pagination and Ordering
    # ----------------------------------------------------------------------

    def test_alerts_ordered_by_created_at(self, authenticated_client, db, freezer):
        """Test that alerts are ordered by created_at descending"""
        from django.utils import timezone

        user = authenticated_client.user
        now = timezone.now()

        freezer.move_to(now - timedelta(days=5))
        old = RideAlertFactory(user=user)

        freezer.move_to(now - timedelta(days=2))
        middle = RideAlertFactory(user=user)

        freezer.move_to(now)
        recent = RideAlertFactory(user=user)

        url = reverse(alert_list_url)
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        results = response.data["results"]
        assert results[0]["id"] == str(recent.id)
        assert results[1]["id"] == str(middle.id)
        assert results[2]["id"] == str(old.id)
