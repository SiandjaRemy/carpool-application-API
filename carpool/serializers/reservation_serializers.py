from rest_framework import serializers

from django.contrib.auth import get_user_model

from accounts.serializers import SimpleUserSerializer

from carpool.models.reservation import Reservation
from carpool.services.reservation_service import ReservationService

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
        read_only_fields = [
            "id",
            "passenger",
            "ride",
            "seats_requested",
            "payment_status",
            "status",
            "created_at",
            "updated_at",
        ]


class CancelReservationSerializer(serializers.Serializer):

    def save(self, **kwargs):
        reservation_id = self.context["reservation_id"]
        user = self.context["user"]

        reservation = ReservationService.cancel_reservation(
            reservation_id=reservation_id, passenger=user
        )

        return {
            "reservation": reservation,
            "detail": "Reservation cancelled successfully",
        }


class PayReservationSerializer(serializers.Serializer):
    payment_method = serializers.CharField(max_length=40, required=True)

    def save(self, **kwargs):
        reservation_id = self.context["reservation_id"]
        user = self.context["user"]

        payment_method = self.validated_data["payment_method"]

        reservation = ReservationService.pay_reservation(
            reservation_id=reservation_id, passenger=user, payment_method=payment_method
        )

        return {
            "reservation": reservation,
            "detail": "Payment completed",
        }
