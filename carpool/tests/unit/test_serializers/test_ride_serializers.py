import pytest

from datetime import timedelta

from django.utils import timezone

from carpool.enums.enums import RideStatus
from carpool.serializers.ride_serializers import RideModelSerializer
from carpool.tests.factories import RideFactory, UserFactory

pytestmark = pytest.mark.unit

ddeparture_datetime = timezone.now() + timedelta(days=1)


class TestRideSerializer:

    def test_serializer_contains_expected_fields(self, db):
        """Test that serializer returns expected fields"""
        ride = RideFactory()
        serializer = RideModelSerializer(ride)

        expected_fields = {
            "id",
            "user",
            "departure_town",
            "arrival_town",
            "departure_datetime",
            "available_seats",
            "price_per_seat",
            "status",
            "fully_reserved",
            "created_at",
            "updated_at",
        }
        assert set(serializer.data.keys()) == expected_fields

    def test_serializer_validates_valid_data(self, db):
        """Test that serializer accepts valid data"""
        user = UserFactory()
        context = {
            "user": user.id,
        }

        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "departure_datetime": (ddeparture_datetime).isoformat(),
            "available_seats": 4,
            "price_per_seat": 25.50,
        }

        serializer = RideModelSerializer(data=data, context=context)
        assert serializer.is_valid()

    def test_serializer_creates_object(self, db):
        """Test that serializer accepts valid data"""
        user = UserFactory()
        context = {
            "user": user,
        }

        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "departure_datetime": (ddeparture_datetime).isoformat(),
            "available_seats": 4,
            "price_per_seat": 25.50,
        }

        serializer = RideModelSerializer(data=data, context=context)
        serializer.is_valid()
        serializer.save()
        assert serializer.data["id"] is not None
        assert serializer.data["status"] == RideStatus.SHECDULED

    def test_serializer_rejects_invalid_data(self, db):
        """Test that serializer rejects invalid data"""
        data = {
            "departure_town": "New York",
            "arrival_town": "Boston",
            "departure_datetime": (ddeparture_datetime).isoformat(),
            "available_seats": -1,  # Invalid
            "price_per_seat": "not decimal",  # Invalid
        }

        serializer = RideModelSerializer(data=data)
        assert not serializer.is_valid()
        assert "available_seats" in serializer.errors
        assert "price_per_seat" in serializer.errors
