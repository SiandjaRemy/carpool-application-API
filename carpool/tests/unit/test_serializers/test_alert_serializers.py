# carpool/tests/unit/test_serializers/test_alert_serializers.py
import pytest
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch

from carpool.serializers.alert_serializers import (
    RideAlertModelSerializer,
    RideAlertUpdateModelSerializer,
)
from carpool.tests.factories import UserFactory, RideAlertFactory

pytestmark = pytest.mark.unit


class TestRideAlertModelSerializer:
    """Tests for the RideAlert serializer"""

    def test_serializer_contains_expected_fields(self, db):
        """Test that serializer returns expected fields"""
        alert = RideAlertFactory()
        serializer = RideAlertModelSerializer(alert)

        expected_fields = {
            "id",
            "user",
            "departure_town",
            "arrival_town",
            "before_date",
            "after_date",
            "is_active",
        }
        assert set(serializer.data.keys()) == expected_fields

    def test_serializer_read_only_fields(self, db):
        """Test that user and is_active are read-only"""

        now = timezone.now()
        data = {
            "departure_town": "Chicago",
            "arrival_town": "Detroit",
            "after_date": now + timedelta(days=1),
            "before_date": now + timedelta(days=7),
            "is_active": False,  # Should be ignored
        }

        user = UserFactory()
        serializer = RideAlertModelSerializer(data=data, context={"user": user})

        assert serializer.is_valid() is True
        assert "is_active" not in serializer.validated_data
        assert serializer.validated_data["departure_town"] == "Chicago"
        assert serializer.validated_data["arrival_town"] == "Detroit"

    def test_create_calls_service(self, db):
        """Test that create method calls the alert service"""
        user = UserFactory()
        now = timezone.now()
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "after_date": now + timedelta(days=1),
            "before_date": now + timedelta(days=7),
        }

        serializer = RideAlertModelSerializer(data=data, context={"user": user})
        assert serializer.is_valid() is True

        with patch(
            "carpool.services.alert_service.RideAlertService.create_alert"
        ) as mock_create:
            mock_create.return_value = RideAlertFactory(**data, user=user)

            alert = serializer.save()

            mock_create.assert_called_once_with(
                user=user, alert_data=serializer.validated_data
            )
            assert alert is not None

    def test_update_calls_service(self, db):
        """Test that update method calls the alert service"""
        user = UserFactory()
        alert = RideAlertFactory(user=user, departure_town="Old City")

        data = {"departure_town": "New City"}

        serializer = RideAlertUpdateModelSerializer(
            instance=alert, data=data, partial=True, context={"user": user}
        )
        assert serializer.is_valid() is True

        with patch(
            "carpool.services.alert_service.RideAlertService.update_alert"
        ) as mock_update:
            mock_update.return_value = alert

            updated_alert = serializer.save()

            mock_update.assert_called_once_with(
                update_data=serializer.validated_data, instance=alert, user=user
            )
            assert updated_alert == alert

    def test_validation_with_dates(self, db):
        """Test validation of date fields"""
        user = UserFactory()
        now = timezone.now()

        # Valid dates
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "after_date": now + timedelta(days=1),
            "before_date": now + timedelta(days=7),
        }

        serializer = RideAlertModelSerializer(data=data, context={"user": user})
        assert serializer.is_valid() is True

    def test_validation_without_dates(self, db):
        """Test validation of date fields"""
        user = UserFactory()

        # Valid dates
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
        }

        serializer = RideAlertModelSerializer(data=data, context={"user": user})
        assert serializer.is_valid() is False
        assert "before_date" in serializer.errors
        assert "after_date" in serializer.errors
