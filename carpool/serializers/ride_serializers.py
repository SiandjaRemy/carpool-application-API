from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.serializers import SimpleUserSerializer
from carpool.models.ride import Ride

User = get_user_model()


class RideModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)

    class Meta:
        model = Ride
        fields = [
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
        ]

        read_only_fields = [
            "id",
            "user",
            "status",
            "fully_reserved",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user

        try:
            with transaction.atomic():
                new_ride = Ride.objects.create(**validated_data)
                # alert_users_for_ride.delay(new_ride.id)
                return new_ride
        except Exception as e:
            raise serializers.ValidationError(str(e))


class RideUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating rides - only allowed fields are updatable"""

    class Meta:
        model = Ride
        fields = [
            "id",
            "departure_town",
            "arrival_town",
            "status",
            "fully_reserved",
            # Updatable fields
            "departure_datetime",
            "available_seats",
            "price_per_seat",
        ]

        read_only_fields = [
            "id",
            "departure_town",
            "arrival_town",
            "status",
            "fully_reserved",
        ]

    def validate_departure_datetime(self, value):
        """Ensure departure time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Departure time must be in the future")
        return value

    def validate_available_seats(self, value):
        """Ensure seats are positive"""
        if value < 0:
            raise serializers.ValidationError("Available seats cannot be negative")
        return value

    def validate_price_per_seat(self, value):
        """Ensure price is positive"""
        if value < 0:
            raise serializers.ValidationError("Price per seat must be positive")
        return value


class SimpleRideModelSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            "id",
            "user_name",
            "departure_town",
            "arrival_town",
            "departure_datetime",
            "available_seats",
            "price_per_seat",
            "fully_reserved",
        ]

    def get_user_name(self, obj: Ride):
        """Returns the ride creator's name"""
        user_name = obj.user.get_full_name()
        return user_name
