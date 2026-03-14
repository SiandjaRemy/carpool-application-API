import pytest

from unittest.mock import patch, MagicMock

from datetime import timedelta

from django.utils import timezone

from carpool.enums.enums import ReservationPaymentStatus, ReservationStatus
from carpool.serializers.reservation_serializers import (
    CancelReservationSerializer,
    PayReservationSerializer,
    ReservationsModelSerializer,
)
from carpool.tests.factories import ReservationFactory, RideFactory, UserFactory

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

    def test_serializer_read_only_fields(self, db):
        """Test that all fields are read-only (no create/update)"""
        data = {
            "seats_requested": 5,
            "payment_status": ReservationPaymentStatus.PAID,
            "status": ReservationStatus.CONFIRMED,
        }
        serializer = ReservationsModelSerializer(data=data)

        # Since all fields are read-only, the serializer should be valid
        # but won't create anything with these fields
        assert serializer.is_valid() is True

        # The validated_data should be empty (no writable fields)
        assert serializer.validated_data == {}

    def test_serializer_with_complete_data(self, db):
        """Test serializer with complete reservation data"""
        reservation = ReservationFactory(seats_requested=3)

        serializer = ReservationsModelSerializer(reservation)
        data = serializer.data

        assert data["id"] == str(reservation.id)
        assert data["seats_requested"] == 3
        assert data["payment_status"] == ReservationPaymentStatus.PENDING
        assert data["status"] == ReservationStatus.PENDING

        # Check nested serializer fields
        assert "passenger" in data
        assert data["passenger"]["id"] == str(reservation.passenger.id)
        assert "ride" in data

    def test_serializer_string_representation(self, db):
        """Test that ride field returns string representation"""
        reservation = ReservationFactory()
        serializer = ReservationsModelSerializer(reservation)

        # The ride field should be a string (StringRelatedField)
        assert isinstance(serializer.data["ride"], str)
        assert str(reservation.ride) in serializer.data["ride"]

    # Tests for the CancelReservationSerializer

    def test_serializer_no_input_fields(self):
        """Test that serializer has no required input fields"""
        serializer = CancelReservationSerializer(data={})
        assert serializer.is_valid() is True
        assert serializer.validated_data == {}

    def test_serializer_save_calls_service(self, db):
        """Test that save method calls the reservation service"""
        user = UserFactory()
        reservation = ReservationFactory(passenger=user)

        # Create serializer with context
        serializer = CancelReservationSerializer(
            data={},
            context={
                "user": user,
                "reservation_id": reservation.id,
            },
        )
        serializer.is_valid()

        # Mock the service method to avoid actual cancellation
        with patch(
            "carpool.services.reservation_service.ReservationService.cancel_reservation"
        ) as mock_cancel:
            mock_cancel.return_value = reservation

            result = serializer.save()

            # Verify service was called with correct args
            mock_cancel.assert_called_once_with(
                reservation_id=reservation.id, passenger=user
            )

            # Verify return structure
            assert result["reservation"] == reservation
            assert result["detail"] == "Reservation cancelled successfully"

    def test_serializer_context_required(self):
        """Test that serializer requires context with user and reservation_id"""
        serializer = CancelReservationSerializer(data={})

        with pytest.raises(KeyError):
            serializer.save()  # Will fail without context

    def test_serializer_service_error_handling(self, db):
        """Test that service errors propagate through serializer"""
        user = UserFactory()
        reservation_id = "123e4567-e89b-12d3-a456-426614174000"

        serializer = CancelReservationSerializer(
            data={},
            context={
                "user": user,
                "reservation_id": reservation_id,
            },
        )
        serializer.is_valid()

        # Mock service to raise an exception
        with patch(
            "carpool.services.reservation_service.ReservationService.cancel_reservation"
        ) as mock_cancel:
            mock_cancel.side_effect = ValueError("Reservation not found")

            with pytest.raises(ValueError, match="Reservation not found"):
                serializer.save()

    # Tests for the PayReservationSerializer

    def test_serializer_requires_payment_method(self):
        """Test that payment_method is required"""
        # Test with missing payment_method
        serializer = PayReservationSerializer(data={})
        assert serializer.is_valid() is False
        assert "payment_method" in serializer.errors

        # Test with empty payment_method
        serializer = PayReservationSerializer(data={"payment_method": ""})
        assert serializer.is_valid() is False
        assert "payment_method" in serializer.errors

    def test_serializer_accepts_valid_payment_method(self):
        """Test that serializer accepts valid payment_method"""
        # Once payment method is included, update this test as you wish
        data = {"payment_method": "stripe_token_123"}
        serializer = PayReservationSerializer(data=data)
        assert serializer.is_valid() is True
        assert serializer.validated_data["payment_method"] == "stripe_token_123"

    def test_serializer_validates_payment_method_length(self):
        """Test that payment_method has max length"""
        # Test with too long payment method (41 chars)
        long_method = "x" * 41
        data = {"payment_method": long_method}
        serializer = PayReservationSerializer(data=data)
        assert serializer.is_valid() is False
        assert "payment_method" in serializer.errors

        # Test with exactly 40 chars
        exact_method = "x" * 40
        data = {"payment_method": exact_method}
        serializer = PayReservationSerializer(data=data)
        assert serializer.is_valid() is True
        assert serializer.validated_data["payment_method"] == exact_method

    def test_serializer_save_calls_service_with_payment_method(self, db):
        """Test that save method passes payment_method to service"""
        user = UserFactory()
        reservation = ReservationFactory(passenger=user)
        payment_method = "stripe_token_xyz"

        serializer = PayReservationSerializer(
            data={"payment_method": payment_method},
            context={
                "user": user,
                "reservation_id": reservation.id,
            },
        )
        serializer.is_valid()

        # Mock the service method
        with patch(
            "carpool.services.reservation_service.ReservationService.pay_reservation"
        ) as mock_pay:
            mock_pay.return_value = reservation

            result = serializer.save()

            # Verify service was called with correct args
            mock_pay.assert_called_once_with(
                reservation_id=reservation.id,
                passenger=user,
                payment_method=payment_method,
            )

            # Verify return structure
            assert result["reservation"] == reservation
            assert result["detail"] == "Payment completed"

    def test_serializer_context_validation(self, db):
        """Test that context contains required fields"""
        user = UserFactory()
        reservation = ReservationFactory(passenger=user)

        # Test missing context
        serializer = PayReservationSerializer(data={"payment_method": "test"})
        serializer.is_valid()

        with pytest.raises(KeyError):
            serializer.save()

        # Test with complete context
        serializer = PayReservationSerializer(
            data={"payment_method": "test"},
            context={
                "user": user,
                "reservation_id": reservation.id,
            },
        )
        serializer.is_valid()

        with patch(
            "carpool.services.reservation_service.ReservationService.pay_reservation"
        ) as mock_pay:
            mock_pay.return_value = reservation
            # Should not raise KeyError
            result = serializer.save()
            assert result is not None

    def test_serializer_payment_method_field_properties(self):
        """Test the properties of the payment_method field"""
        field = PayReservationSerializer().fields["payment_method"]

        assert field.required is True
        assert field.max_length == 40
        assert field.allow_blank is False
        assert field.allow_null is False

    def test_serializer_service_error_handling(self, db):
        """Test that service errors propagate through serializer"""
        user = UserFactory()
        reservation_id = "123e4567-e89b-12d3-a456-426614174000"

        serializer = PayReservationSerializer(
            data={"payment_method": "test_token"},
            context={
                "user": user,
                "reservation_id": reservation_id,
            },
        )
        serializer.is_valid()

        # Mock service to raise various exceptions
        with patch(
            "carpool.services.reservation_service.ReservationService.pay_reservation"
        ) as mock_pay:
            # Test ValueError
            mock_pay.side_effect = ValueError("Payment failed")
            with pytest.raises(ValueError, match="Payment failed"):
                serializer.save()

            # Test PermissionError
            mock_pay.side_effect = PermissionError("Not your reservation")
            with pytest.raises(PermissionError, match="Not your reservation"):
                serializer.save()

            # Test generic Exception
            mock_pay.side_effect = Exception("Unexpected error")
            with pytest.raises(Exception, match="Unexpected error"):
                serializer.save()
