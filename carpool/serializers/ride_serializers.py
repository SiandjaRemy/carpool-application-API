from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from accounts.serializers import SimpleUserSerializer
from carpool.models.ride import Ride
from carpool.services.ride_service import RideService

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

        new_ride = RideService.create_ride(ride_data=validated_data, user=user)

        return new_ride


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

    def update(self, instance, validated_data):
        user = self.context["user"]
        validated_data["user"] = user

        updated_ride = RideService.update_ride(
            update_data=validated_data, instance=instance, user=user
        )

        return updated_ride


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
