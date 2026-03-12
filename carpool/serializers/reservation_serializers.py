from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.serializers import SimpleUserSerializer

from carpool.enums.enums import RideStatus
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
