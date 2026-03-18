import pytest
from carpool.models import RideAlert
from carpool.tests.factories import UserFactory, RideAlertFactory

pytestmark = pytest.mark.unit


class TestRideAlertModel:
    """Unit tests for the RideAlert model"""

    def test_create_alert(self, db):
        """Test creating a ride alert with valid data"""
        user = UserFactory()
        alert = RideAlertFactory(
            user=user,
            departure_town="New York",
            arrival_town="Boston",
        )

        assert alert.id is not None
        assert alert.user == user
        assert alert.departure_town == "New York"
        assert alert.arrival_town == "Boston"
        assert alert.is_active is True

    def test_alert_str_method(self, db):
        """Test the string representation of the alert"""
        alert = RideAlertFactory(
            departure_town="New York",
            arrival_town="Boston",
        )
        expected_str = f"Alert for {alert.user} from New York to Boston"
        assert str(alert) == expected_str

    def test_alert_with_dates(self, db):
        """Test alert with date filters"""
        from django.utils import timezone
        from datetime import timedelta

        alert = RideAlertFactory(
            departure_town="New York",
            arrival_town="Boston",
            before_date=timezone.now() + timedelta(days=7),
            after_date=timezone.now() + timedelta(days=1),
        )

        assert alert.before_date is not None
        assert alert.after_date is not None
        assert alert.after_date < alert.before_date

    def test_alert_indexes(self, db):
        """Test that model has proper indexes"""
        indexes = RideAlert._meta.indexes
        index_fields = [idx.fields for idx in indexes]

        assert ["departure_town", "arrival_town"] in index_fields
        assert ["is_active"] in index_fields

    def test_cascade_delete_on_user(self, db):
        """Test that alerts are deleted when user is deleted"""
        user = UserFactory()
        alert = RideAlertFactory(user=user)

        user.delete()

        with pytest.raises(RideAlert.DoesNotExist):
            alert.refresh_from_db()
