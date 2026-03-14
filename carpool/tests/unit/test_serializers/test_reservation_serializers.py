import pytest

from datetime import timedelta

from django.utils import timezone

from carpool.serializers.reservation_serializers import ReservationsModelSerializer
from carpool.tests.factories import ReservationFactory, RideFactory

pytestmark = pytest.mark.unit

ddeparture_datetime = timezone.now() + timedelta(days=1)


class TestReservationSerializer:

    # This is the only test needed since reservations are not created manually for now
    def test_serializer_contains_expected_fields(self, db):
        """Test that serializer returns expected fields"""
        ride = RideFactory()
        reservation = ReservationFactory(ride=ride)
        serializer = ReservationsModelSerializer(reservation)

        print(f"Serializer data is: {serializer.data}")
        expected_fields = {
            "id",
            "passenger",
            "ride",
            "seats_requested",
            "payment_status",
            "status",
            "created_at",
            "updated_at",
        }

        assert set(serializer.data.keys()) == expected_fields
        assert str(ride) == serializer.data["ride"]
