from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.serializers import SimpleUserSerializer
from passengers.models import Passenger
from rides.models import Ride

User = get_user_model()


class RegisterPassengerModelSerializer(serializers.Serializer):
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
                {"message": "You cant reserve a seat for a ride you created"}
            )

        if number_of_seats > ride.available_seats:
            raise serializers.ValidationError(
                {
                    "message": f"Only {ride.available_seats} seats are available for this ride"
                }
            )
        try:
            with transaction.atomic():
                passenger = Passenger.objects.create(**validated_data)
                ride.available_seats -= passenger.number_of_seats
                if ride.available_seats == 0:
                    ride.is_full = True
                ride.save()
                return passenger
        except Exception as e:
            raise serializers.ValidationError(str(e))



class PassengerModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)
    ride = serializers.StringRelatedField()
    ride_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = Passenger
        fields = [
            "id",
            "user",
            "ride",
            "ride_id",
            "number_of_seats",
            "created_at",
            "modified_at",
        ]

        read_only_fields = ["user", "ride"]

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
                {"message": "You cant reserve a seat for a ride you created"}
            )

        if number_of_seats > ride.available_seats:
            raise serializers.ValidationError(
                {
                    "message": f"Only {ride.available_seats} seats are available for this ride"
                }
            )
        try:
            with transaction.atomic():
                passenger = Passenger.objects.create(**validated_data)
                ride.available_seats -= passenger.number_of_seats
                if ride.available_seats == 0:
                    ride.is_full = True
                ride.save()
                return passenger
        except Exception as e:
            raise serializers.ValidationError(str(e))


