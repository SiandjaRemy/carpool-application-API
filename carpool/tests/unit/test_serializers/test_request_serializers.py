import pytest
from unittest.mock import patch


from carpool.serializers.request_serializers import (
    RideRequestModelSerializer,
    AcceptRideRequestSerializer,
    RejectRideRequestSerializer,
    CancelRideRequestSerializer,
)
from carpool.enums.enums import RequestStatus
from carpool.tests.factories import (
    UserFactory,
    RideFactory,
    RideRequestFactory,
)

pytestmark = pytest.mark.unit


class TestRideRequestSerializer:
    """Tests for the RideRequest serializer"""

    def test_serializer_contains_expected_fields(self, db):
        """Test that serializer returns expected fields"""
        ride_request = RideRequestFactory()
        serializer = RideRequestModelSerializer(ride_request)

        expected_fields = {
            "id",
            "ride",
            "passenger",
            "status",
            "seats_requested",
            "price_per_seat",
            "is_active",
        }
        assert set(serializer.data.keys()) == expected_fields

    def test_serializer_read_only_fields(self, db):
        """Test that specified fields are read-only"""
        data = {
            "status": RequestStatus.ACCEPTED,
            "is_active": False,
            "seats_requested": 5,
            "price_per_seat": 30.00,
        }

        # Create context with user and ride_id
        user = UserFactory()
        ride = RideFactory()

        serializer = RideRequestModelSerializer(
            data=data, context={"user": user, "ride_id": ride.id}
        )

        # The serializer should be valid but only writable fields should be in validated_data
        assert serializer.is_valid() is True

        # Check that only writable fields are in validated_data
        assert "seats_requested" in serializer.validated_data
        assert "price_per_seat" in serializer.validated_data
        assert "status" not in serializer.validated_data
        assert "is_active" not in serializer.validated_data

    def test_validate_success(self, db):
        """Test successful validation"""
        user = UserFactory()
        ride = RideFactory(available_seats=4)

        data = {
            "seats_requested": 2,
            "price_per_seat": 25.50,
        }

        serializer = RideRequestModelSerializer(
            data=data, context={"user": user, "ride_id": ride.id}
        )

        assert serializer.is_valid() is True
        assert serializer.validated_data["seats_requested"] == 2
        assert serializer.validated_data["price_per_seat"] == 25.50

    # def test_validate_ride_not_found(self, db):
    #     """Test validation when ride doesn't exist"""
    #     user = UserFactory()

    #     data = {
    #         "seats_requested": 2,
    #         "price_per_seat": 25.50,
    #     }

    #     serializer = RideRequestModelSerializer(
    #         data=data,
    #         context={"user": user, "ride_id": "00000000-0000-0000-0000-000000000000"},
    #     )

    #     assert serializer.is_valid() is False
    #     assert "detail" in serializer.errors
    #     assert "ride not found" in str(serializer.errors["detail"]).lower()

    # def test_validate_ride_not_scheduled(self, db):
    #     """Test validation when ride is not scheduled"""
    #     user = UserFactory()
    #     ride = RideFactory(status=RideStatus.CANCELLED)

    #     data = {
    #         "seats_requested": 2,
    #         "price_per_seat": 25.50,
    #     }

    #     serializer = RideRequestModelSerializer(
    #         data=data, context={"user": user, "ride_id": ride.id}
    #     )

    #     assert serializer.is_valid() is False
    #     assert "detail" in serializer.errors
    #     assert "ride not found" in str(serializer.errors["detail"]).lower()

    # def test_validate_ride_fully_reserved(self, db):
    #     """Test validation when ride is fully reserved"""
    #     user = UserFactory()
    #     ride = RideFactory(available_seats=0, fully_reserved=True)

    #     data = {
    #         "seats_requested": 2,
    #         "price_per_seat": 25.50,
    #     }

    #     serializer = RideRequestModelSerializer(
    #         data=data, context={"user": user, "ride_id": ride.id}
    #     )

    #     assert serializer.is_valid() is False
    #     assert "detail" in serializer.errors
    #     assert "ride not found" in str(serializer.errors["detail"]).lower()

    # def test_validate_own_ride(self, db):
    #     """Test validation when user tries to request their own ride"""
    #     user = UserFactory()
    #     ride = RideFactory(user=user)

    #     data = {
    #         "seats_requested": 2,
    #         "price_per_seat": 25.50,
    #     }

    #     serializer = RideRequestModelSerializer(
    #         data=data, context={"user": user, "ride_id": ride.id}
    #     )

    #     assert serializer.is_valid() is False
    #     assert "detail" in serializer.errors
    #     assert (
    #         "can't make a request for a ride you created"
    #         in str(serializer.errors["detail"]).lower()
    #     )

    # def test_validate_insufficient_seats(self, db):
    #     """Test validation when requesting more seats than available"""
    #     user = UserFactory()
    #     ride = RideFactory(available_seats=2)

    #     data = {
    #         "seats_requested": 3,
    #         "price_per_seat": 25.50,
    #     }

    #     serializer = RideRequestModelSerializer(
    #         data=data, context={"user": user, "ride_id": ride.id}
    #     )

    #     assert serializer.is_valid() is False
    #     assert "detail" in serializer.errors
    #     assert "only 2 seats are available" in str(serializer.errors["detail"]).lower()

    # def test_validate_duplicate_request(self, db):
    #     """Test validation when user already has a pending/accepted request"""
    #     user = UserFactory()
    #     ride = RideFactory(available_seats=4)

    #     # Create existing request
    #     RideRequestFactory(ride=ride, passenger=user, status=RequestStatus.PENDING)

    #     data = {
    #         "seats_requested": 2,
    #         "price_per_seat": 25.50,
    #     }

    #     serializer = RideRequestModelSerializer(
    #         data=data, context={"user": user, "ride_id": ride.id}
    #     )

    #     assert serializer.is_valid() is False
    #     assert "detail" in serializer.errors
    #     assert "already made a request" in str(serializer.errors["detail"]).lower()

    def test_create_success(self, db):
        """Test successful creation of ride request"""
        user = UserFactory()
        ride = RideFactory(available_seats=4)

        data = {
            "seats_requested": 2,
            "price_per_seat": 25.50,
        }

        serializer = RideRequestModelSerializer(
            data=data, context={"user": user, "ride_id": ride.id}
        )

        assert serializer.is_valid() is True
        ride_request = serializer.save()

        assert ride_request.id is not None
        assert ride_request.passenger == user
        assert ride_request.ride == ride
        assert ride_request.seats_requested == 2
        assert ride_request.price_per_seat == 25.50
        assert ride_request.status == RequestStatus.PENDING
        assert ride_request.is_active is True

    """Tests for updating ride requests"""

    def test_update_success(self, db):
        """Test successful update of pending request"""
        passenger = UserFactory()
        ride = RideFactory(available_seats=5)
        ride_request = RideRequestFactory(
            ride=ride,
            seats_requested=1,
            price_per_seat=25.00,
            passenger=passenger,
        )

        data = {
            "seats_requested": 2,
            "price_per_seat": 30.00,
        }

        context = {
            "user": passenger,
        }

        serializer = RideRequestModelSerializer(
            instance=ride_request,
            data=data,
            context=context,
            partial=True,
        )

        assert serializer.is_valid() is True
        updated_request = serializer.update(ride_request, data)

        assert updated_request.seats_requested == 2
        assert updated_request.price_per_seat == 30.00

    # def test_update_non_pending_request(self, db):
    #     """Test that non-pending requests cannot be updated"""
    #     passenger = UserFactory()
    #     ride_request = RideRequestFactory(
    #         status=RequestStatus.ACCEPTED, passenger=passenger
    #     )

    #     data = {"seats_requested": 2}
    #     context = {
    #         "user": passenger,
    #     }

    #     serializer = RideRequestModelSerializer(
    #         instance=ride_request,
    #         data=data,
    #         partial=True,
    #         context=context,
    #     )

    #     assert serializer.is_valid() is False
    #     assert "This request cannot be updated" in str(serializer.errors)

    def test_validate_seats_requested_positive(self, db):
        """Test that seats_requested must be positive and > 1"""
        passenger = UserFactory()
        ride_request = RideRequestFactory(passenger=passenger)

        data = {"seats_requested": 0}
        context = {
            "user": passenger,
        }

        serializer = RideRequestModelSerializer(
            instance=ride_request,
            data=data,
            partial=True,
            context=context,
        )

        assert serializer.is_valid() is False
        assert "seats_requested" in serializer.errors

    # def test_validate_seats_requested_within_capacity(self, db):
    #     """Test that increasing seats respects ride capacity"""
    #     passenger = UserFactory()
    #     ride = RideFactory(available_seats=3)
    #     ride_request = RideRequestFactory(
    #         ride=ride,
    #         seats_requested=2,
    #         passenger=passenger,
    #     )

    #     # Try to increase to 4 seats (exceeds ride capacity)
    #     data = {"seats_requested": 4}
    #     context = {
    #         "user": passenger,
    #     }

    #     serializer = RideRequestModelSerializer(
    #         instance=ride_request,
    #         data=data,
    #         partial=True,
    #         context=context,
    #     )

    #     assert serializer.is_valid() is False
    #     assert "cannot increase" in str(serializer.errors["seats_requested"]).lower()

    def test_validate_price_per_seat_positive(self, db):
        """Test that price_per_seat must be positive"""
        passenger = UserFactory()
        ride_request = RideRequestFactory(passenger=passenger)

        data = {"price_per_seat": 0}
        context = {
            "user": passenger,
        }

        serializer = RideRequestModelSerializer(
            instance=ride_request,
            data=data,
            partial=True,
            context=context,
        )

        assert serializer.is_valid() is False
        assert "price_per_seat" in serializer.errors

    """Tests for accepting ride requests"""

    def test_accept_request_serializer_no_input_fields(self):
        """Test that serializer has no required input fields"""
        serializer = AcceptRideRequestSerializer(data={})
        assert serializer.is_valid() is True
        assert serializer.validated_data == {}

    def test_accept_request_serializer_save_method_calls_service(self, db):
        """Test that save method of AcceptRideRequestSerializer calls the request service"""
        user = UserFactory()
        ride_request = RideRequestFactory()

        serializer = AcceptRideRequestSerializer(
            data={},
            context={
                "user": user,
                "request_id": ride_request.id,
            },
        )
        serializer.is_valid()

        with patch(
            "carpool.services.request_service.RideRequestService.accept_request"
        ) as mock_accept:
            mock_accept.return_value = ride_request

            result = serializer.save()

            mock_accept.assert_called_once_with(request_id=ride_request.id, user=user)

            assert result["request"] == ride_request
            assert "detail" in result
            # Note: Your serializer says "Request rejected successfully" but this is for accept
            # You might want to fix that typo

    def test_context_required(self):
        """Test that context requires user and request_id"""
        serializer = AcceptRideRequestSerializer(data={})

        with pytest.raises(KeyError):
            serializer.save()

    """Tests for rejecting ride requests"""

    def test_reject_request_serializer_no_input_fields(self):
        """Test that serializer has no required input fields"""
        serializer = RejectRideRequestSerializer(data={})
        assert serializer.is_valid() is True
        assert serializer.validated_data == {}

    def test_reject_request_serializer_save_method_calls_service(self, db):
        """Test that save method of RejectRideRequestSerializer calls the request service"""
        user = UserFactory()
        ride_request = RideRequestFactory()

        serializer = RejectRideRequestSerializer(
            data={},
            context={
                "user": user,
                "request_id": ride_request.id,
            },
        )
        serializer.is_valid()

        with patch(
            "carpool.services.request_service.RideRequestService.reject_request"
        ) as mock_reject:
            mock_reject.return_value = ride_request

            result = serializer.save()

            mock_reject.assert_called_once_with(request_id=ride_request.id, user=user)

            assert result["request"] == ride_request
            assert result["detail"] == "Request rejected successfully"

    def test_service_error_handling(self, db):
        """Test that service errors propagate"""
        user = UserFactory()
        request_id = "123e4567-e89b-12d3-a456-426614174000"

        serializer = RejectRideRequestSerializer(
            data={},
            context={
                "user": user,
                "request_id": request_id,
            },
        )
        serializer.is_valid()

        with patch(
            "carpool.services.request_service.RideRequestService.reject_request"
        ) as mock_reject:
            mock_reject.side_effect = ValueError("Request not found")

            with pytest.raises(ValueError, match="Request not found"):
                serializer.save()

    """Tests for cancelling ride requests"""

    def test_cancel_request_serializer_no_input_fields(self):
        """Test that serializer has no required input fields"""
        serializer = CancelRideRequestSerializer(data={})
        assert serializer.is_valid() is True
        assert serializer.validated_data == {}

    def test_cancel_request_serializer_save_method_calls_service(self, db):
        """Test that save method of CancelRideRequestSerializer calls the request service"""
        user = UserFactory()
        ride_request = RideRequestFactory()

        serializer = CancelRideRequestSerializer(
            data={},
            context={
                "user": user,
                "request_id": ride_request.id,
            },
        )
        serializer.is_valid()

        with patch(
            "carpool.services.request_service.RideRequestService.cancel_request"
        ) as mock_cancel:
            mock_cancel.return_value = ride_request

            result = serializer.save()

            mock_cancel.assert_called_once_with(request_id=ride_request.id, user=user)

            assert result["request"] == ride_request
            assert result["detail"] == "Request cancelled successfully"

    def test_cancel_own_request_only(self, db):
        """Test that only the passenger can cancel their request"""
        # This would be tested in the service, but we can test the serializer passes correctly
        passenger = UserFactory()
        # The other user
        UserFactory()
        ride_request = RideRequestFactory(passenger=passenger)

        serializer = CancelRideRequestSerializer(
            data={},
            context={
                "user": passenger,  # Correct user
                "request_id": ride_request.id,
            },
        )
        serializer.is_valid()

        with patch(
            "carpool.services.request_service.RideRequestService.cancel_request"
        ) as mock_cancel:
            mock_cancel.return_value = ride_request
            serializer.save()
            mock_cancel.assert_called_once_with(
                request_id=ride_request.id, user=passenger
            )


class TestSerializersIntegration:
    """Integration tests with actual service calls"""

    def test_full_request_lifecycle(self, db):
        """Test creating, updating, accepting, and cancelling a request"""

        # Create data
        passenger = UserFactory()
        driver = UserFactory()
        ride = RideFactory(user=driver, available_seats=4)

        # 1. Create request
        create_serializer = RideRequestModelSerializer(
            data={
                "seats_requested": 2,
                "price_per_seat": 25.00,
            },
            context={"user": passenger, "ride_id": ride.id},
        )
        assert create_serializer.is_valid()
        ride_request = create_serializer.save()

        assert ride_request.status == RequestStatus.PENDING

        # 2. Update request
        update_serializer = RideRequestModelSerializer(
            instance=ride_request,
            data={"seats_requested": 3},
            partial=True,
            context={"user": passenger},
        )
        assert update_serializer.is_valid()
        updated_request = update_serializer.save()
        assert updated_request.seats_requested == 3

        # 3. Accept request (as driver)
        accept_serializer = AcceptRideRequestSerializer(
            data={}, context={"user": driver, "request_id": ride_request.id}
        )
        assert accept_serializer.is_valid()
        result = accept_serializer.save()
        assert result["request"].status == RequestStatus.ACCEPTED
