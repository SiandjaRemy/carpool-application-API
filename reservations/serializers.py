from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.serializers import SimpleUserSerializer
from reservations.models import Reservation
from rides.models import Ride

User = get_user_model()


class MakeReservationModelSerializer(serializers.Serializer):
    ride_id = serializers.UUIDField(required=True)
    number_of_seats = serializers.IntegerField(required=True)

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user

        ride_id = validated_data["ride_id"]
        number_of_seats = validated_data["number_of_seats"]

        ride = Ride.objects.select_related("user").filter(id=ride_id).first()
        if ride is None:
            raise serializers.ValidationError(
                {"message": "Corresponding ride not found"}
            )

        if ride.user == user:
            raise serializers.ValidationError(
                {"message": "You can't reserve a seat for a ride you created"}
            )

        if number_of_seats > ride.available_seats:
            raise serializers.ValidationError(
                {
                    "message": f"Only {ride.available_seats} seats are available for this ride"
                }
            )
        try:
            with transaction.atomic():
                reservation = Reservation.objects.create(**validated_data)
                ride.available_seats -= reservation.number_of_seats
                if ride.available_seats == 0:
                    ride.is_full = True
                ride.save()
                return reservation
        except Exception as e:
            raise serializers.ValidationError(str(e))


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
            "number_of_seats",
            "created_at",
            "modified_at",
        ]

        read_only_fields = ["id", "user", "ride"]

    def validate(self, attrs):
        user = self.context["user"]

        ride_id = attrs.get("ride_id")
        number_of_seats = attrs.get("number_of_seats")

        ride = Ride.objects.select_related("user").filter(id=ride_id).first()
        if ride is None:
            raise serializers.ValidationError(
                {"message": "Corresponding ride not found"}
            )

        if ride.user == user:
            raise serializers.ValidationError(
                {"message": "You cant reserve a seat for a ride you created"}
            )

        if number_of_seats > ride.available_seats:
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
                ride.available_seats -= reservation.number_of_seats
                if ride.available_seats == 0:
                    ride.is_full = True
                ride.save()
                return reservation
        except Exception as e:
            raise serializers.ValidationError(str(e))
