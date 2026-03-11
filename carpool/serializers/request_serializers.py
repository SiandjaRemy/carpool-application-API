from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.serializers import SimpleUserSerializer

from carpool.enums.enums import RequestStatus, RideStatus
from carpool.models import RideRequest, Ride
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
            .filter(id=ride_id, status=RideStatus.SHECDULED, fully_reserved=False)
            .first()
        )
        if ride is None:
            raise serializers.ValidationError(
                {"message": "Corresponding ride not found"}
            )

        if ride.user == user:
            raise serializers.ValidationError(
                {"message": "You can't make a request for a ride you created"}
            )

        if seats_requested > ride.available_seats:
            raise serializers.ValidationError(
                {
                    "message": f"Only {ride.available_seats} seats are available for this ride"
                }
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
