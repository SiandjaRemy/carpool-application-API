from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.serializers import SimpleUserSerializer

from carpool.models.reservation import Reservation
from carpool.models.ride import Ride

User = get_user_model()


class ReservationsModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)
    ride = serializers.StringRelatedField()
    ride_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "user",
            "ride",
            "ride_id",
            "seats_requested",
            "created_at",
            "modified_at",
        ]

        read_only_fields = ["id", "user", "ride"]

    def validate(self, attrs):
        user = self.context["user"]

        ride_id = attrs.get("ride_id")
        seats_requested = attrs.get("seats_requested")

        ride = Ride().objects.select_related("user").filter(id=ride_id).first()
        if ride is None:
            raise serializers.ValidationError(
                {"message": "Corresponding ride not found"}
            )

        if ride.user == user:
            raise serializers.ValidationError(
                {"message": "You cant reserve a seat for a ride you created"}
            )

        if seats_requested > ride.available_seats:
            raise serializers.ValidationError(
                {
                    "message": f"Only {ride.available_seats} seats are available for this ride"
                }
            )

        attrs["ride"] = ride

        return attrs

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user

        ride: Ride = validated_data["ride"]

        try:
            with transaction.atomic():
                reservation = Reservation.objects.create(**validated_data)
                ride.available_seats -= reservation.seats_requested
                if ride.available_seats == 0:
                    ride.is_full = True
                ride.save()
                return reservation
        except Exception as e:
            raise serializers.ValidationError(str(e))
