from rest_framework import serializers

from django.contrib.auth import get_user_model

from accounts.serializers import SimpleUserSerializer

from carpool.models.reservation import Reservation

User = get_user_model()


class ReservationsModelSerializer(serializers.ModelSerializer):
    passenger = SimpleUserSerializer(many=False, read_only=True)
    ride = serializers.StringRelatedField()

    class Meta:
        model = Reservation
        fields = [
            "id",
            "passenger",
            "ride",
            "seats_requested",
            "payment_status",
            "status",
            "created_at",
            "updated_at",
        ]
