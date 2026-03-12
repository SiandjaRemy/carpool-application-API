from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.serializers import SimpleUserSerializer

from carpool.enums.enums import RequestStatus, RideStatus
from carpool.models import RideRequest, Ride
from carpool.models.reservation import Reservation
from carpool.serializers.ride_serializers import SimpleRideModelSerializer
from carpool.validators.ride_request_validators import validate_ride_request_exists

User = get_user_model()


class RideRequestModelSerializer(serializers.ModelSerializer):
    passenger = SimpleUserSerializer(many=False, read_only=True)
    ride = SimpleRideModelSerializer(many=False, read_only=True)

    class Meta:
        model = RideRequest
        fields = [
            "id",
            "ride",
            "passenger",
            "status",
            "seats_requested",
            "price_per_seat",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "ride",
            "status",
            "passenger",
            "is_active",
        ]

    def validate(self, attrs):
        user = self.context["user"]
        ride_id = self.context["ride_id"]

        seats_requested = attrs.get("seats_requested")

        validate_ride_request_exists(ride_id, user)

        ride = (
            Ride.objects.select_related("user")
            .filter(id=ride_id, status=RideStatus.SCHEDULED, fully_reserved=False)
            .first()
        )
        if ride is None:
            raise serializers.ValidationError(
                {"detail": "Corresponding ride not found"}
            )

        if ride.user == user:
            raise serializers.ValidationError(
                {"detail": "You can't make a request for a ride you created"}
            )

        if seats_requested > ride.available_seats:
            if ride.available_seats == 0:
                raise serializers.ValidationError(detail=f"This ride is fully reserved")
            else:
                raise serializers.ValidationError(
                    detail=f"Only {ride.available_seats} seats are available for this ride"
                )

        attrs["ride_id"] = ride_id

        return attrs

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["passenger"] = user

        try:
            with transaction.atomic():
                new_ride_request = RideRequest.objects.create(**validated_data)
                return new_ride_request
        except Exception as e:
            raise serializers.ValidationError(str(e))


class RideRequestUpdateModelSerializer(serializers.ModelSerializer):
    """Serializer for updating pending ride requests - only allowed fields are updatable"""

    class Meta:
        model = RideRequest
        fields = [
            "id",
            "seats_requested",
            "price_per_seat",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if self.instance.status != RequestStatus.PENDING:
            raise serializers.ValidationError("This request cannot be updated.")
        return super().validate(attrs)

    def validate_seats_requested(self, value):
        """Validate seats are positive and within ride capacity"""
        if value <= 0:
            raise serializers.ValidationError("Seats requested must be positive.")

        # Check against ride's available seats
        if self.instance:
            ride = self.instance.ride
            current_seats = self.instance.seats_requested

            # If increasing seats, check availability
            if value > current_seats:
                additional_seats = value - current_seats
                if ride.available_seats < value:
                    raise serializers.ValidationError(
                        f"Cannot increase by {additional_seats}. Only {ride.available_seats} seats available."
                    )

        return value

    def validate_price_per_seat(self, value):
        """Ensure price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price per seat must be positive.")
        return value

    def update(self, instance, validated_data):
        # Update the request fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class AcceptRideRequestSerializer(serializers.Serializer):

    def validate(self, attrs):
        user = self.context["user"]
        ride_id = self.context["ride_id"]
        request_id = self.context["request_id"]

        try:
            # Get the request with related ride in a single query
            request = RideRequest.objects.select_related("ride").get(
                id=request_id,
                ride_id=ride_id,
                ride__user=user,  # Ensure current user owns the ride
                ride__status=RideStatus.SCHEDULED,
                status=RequestStatus.PENDING,
            )
        except RideRequest.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "Corresponding pending request not found."}
            )

        # Validate that the ride hasn't already departed
        if request.ride.departure_datetime <= timezone.now():
            raise serializers.ValidationError(
                {
                    "detail": "Cannot accept requests for rides that have already departed."
                }
            )

        # Validate seat availability
        if request.seats_requested > request.ride.available_seats:
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"Cannot accept request. Only {request.ride.available_seats} seats available, "
                        f"but {request.seats_requested} requested."
                    )
                }
            )

        # Store the request in attrs for use in save()
        attrs["ride_request"] = request
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        """
        Atomic transaction that:
        1. Updates the request status to ACCEPTED
        2. Decreases available seats on the ride
        3. Creates a reservation
        """
        ride_request = self.validated_data["ride_request"]

        # Lock the ride and request rows to prevent race conditions
        ride = ride_request.ride
        ride = Ride.objects.select_for_update().get(id=ride.id)
        ride_request = RideRequest.objects.select_for_update().get(id=ride_request.id)

        # Double-check status and availability within transaction
        if ride_request.status != RequestStatus.PENDING:
            raise serializers.ValidationError(
                {
                    "detail": f"Request is no longer pending (current status: {ride_request.status})"
                }
            )

        if ride_request.seats_requested > ride.available_seats:
            raise serializers.ValidationError(
                {
                    "detail": f"Seat availability changed. Only {ride.available_seats} seats left."
                }
            )

        # 1. Update request status
        ride_request.status = RequestStatus.ACCEPTED
        ride_request.save(update_fields=["status", "updated_at"])

        # 2. Update ride available seats
        ride.available_seats -= ride_request.seats_requested
        ride.save(update_fields=["available_seats", "updated_at"])

        # 3. Create reservation
        reservation = Reservation.objects.create(
            ride=ride,
            passenger=ride_request.passenger,
            seats_requested=ride_request.seats_requested,
            price_per_seat=ride.price_per_seat,
        )

        # Optional: Trigger background tasks
        # from carpool.tasks import send_request_accepted_notification
        # transaction.on_commit(lambda: send_request_accepted_notification.delay(
        #     request_id=ride_request.id,
        #     reservation_id=reservation.id
        # ))

        return {
            "request": ride_request,
            "reservation": reservation,
            "detail": "Request accepted successfully",
        }


class RejectRideRequestSerializer(serializers.Serializer):

    def validate(self, attrs):
        user = self.context["user"]
        ride_id = self.context["ride_id"]
        request_id = self.context["request_id"]

        try:
            # Get the request with related ride in a single query
            request = RideRequest.objects.select_related("ride").get(
                id=request_id,
                ride_id=ride_id,
                ride__user=user,  # Ensure current user owns the ride
                ride__status=RideStatus.SCHEDULED,
                status=RequestStatus.PENDING,
            )
        except RideRequest.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "Corresponding pending request not found."}
            )

        # Validate that the ride hasn't already departed
        if request.ride.departure_datetime <= timezone.now():
            raise serializers.ValidationError(
                {
                    "detail": "Cannot reject requests for rides that have already departed."
                }
            )

        # Validate seat availability
        if request.seats_requested > request.ride.available_seats:
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"Cannot accept request. Only {request.ride.available_seats} seats available, "
                        f"but {request.seats_requested} requested."
                    )
                }
            )

        # Store the request in attrs for use in save()
        attrs["ride_request"] = request
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        """
        Atomic transaction that updates the request status to REJECTED
        """
        ride_request = self.validated_data["ride_request"]

        # Lock the ride and request rows to prevent race conditions
        ride = ride_request.ride
        ride_request = RideRequest.objects.select_for_update().get(id=ride_request.id)

        # Double-check status and availability within transaction
        if ride_request.status != RequestStatus.PENDING:
            raise serializers.ValidationError(
                {
                    "detail": f"Request is no longer pending (current status: {ride_request.status})"
                }
            )

        if ride_request.seats_requested > ride.available_seats:
            raise serializers.ValidationError(
                {
                    "detail": f"Seat availability changed. Only {ride.available_seats} seats left."
                }
            )

        ride_request.status = RequestStatus.REJECTED
        ride_request.save(update_fields=["status", "updated_at"])

        # Optional: Trigger background tasks
        # from carpool.tasks import send_request_rejected_notification
        # transaction.on_commit(lambda: send_request_rejected_notification.delay(
        #     request_id=ride_request.id,
        #     reservation_id=reservation.id
        # ))

        return {
            "request": ride_request,
            "detail": "Request rejected successfully",
        }


class CancelRideRequestSerializer(serializers.Serializer):

    def validate(self, attrs):
        user = self.context["user"]
        ride_id = self.context["ride_id"]
        request_id = self.context["request_id"]

        try:
            # Get the request with related ride in a single query
            request = RideRequest.objects.select_related("ride").get(
                id=request_id,
                ride_id=ride_id,
                passenger=user,  # Ensure current user is the passenger on the request
                ride__status=RideStatus.SCHEDULED,
                status=RequestStatus.PENDING,
            )
        except RideRequest.DoesNotExist:
            raise serializers.ValidationError(
                {"detail": "Corresponding pending request not found."}
            )

        # Store the request in attrs for use in save()
        attrs["ride_request"] = request
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        """
        Atomic transaction that updates the request status to REJECTED
        """
        ride_request = self.validated_data["ride_request"]

        # Lock the ride and request rows to prevent race conditions
        ride = ride_request.ride
        ride_request = RideRequest.objects.select_for_update().get(id=ride_request.id)

        # Double-check status and availability within transaction
        if ride_request.status != RequestStatus.PENDING:
            raise serializers.ValidationError(
                {
                    "detail": f"Request is no longer pending (current status: {ride_request.status})"
                }
            )

        if ride_request.seats_requested > ride.available_seats:
            raise serializers.ValidationError(
                {
                    "detail": f"Seat availability changed. Only {ride.available_seats} seats left."
                }
            )

        ride_request.status = RequestStatus.CANCELLED
        ride_request.save(update_fields=["status", "updated_at"])

        return {
            "request": ride_request,
            "detail": "Request cancelled successfully",
        }
