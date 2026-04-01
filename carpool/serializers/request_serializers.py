from rest_framework import serializers

from django.contrib.auth import get_user_model

from accounts.serializers import SimpleUserSerializer

from carpool.models import RideRequest
from carpool.serializers.ride_serializers import SimpleRideModelSerializer
from carpool.services.request_service import RideRequestService

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

    def create(self, validated_data):
        user = self.context["user"]
        ride_id = self.context["ride_id"]

        ride_request = RideRequestService.create_request(
            ride_id=ride_id, passenger=user, request_data=validated_data
        )

        return ride_request

    def update(self, instance, validated_data):
        user = self.context["user"]
        request_id = self.context["request_id"]

        updated_request = RideRequestService.update_request(
            request_id=request_id, update_data=validated_data, passenger=user
        )

        return updated_request


class AcceptRideRequestSerializer(serializers.Serializer):

    def save(self, **kwargs):
        request_id = self.context["request_id"]
        user = self.context["user"]

        ride_request = RideRequestService.accept_request(
            request_id=request_id, user=user
        )

        return {
            "request": ride_request,
            "detail": "Request rejected successfully",
        }


class RejectRideRequestSerializer(serializers.Serializer):

    def save(self, **kwargs):
        request_id = self.context["request_id"]
        user = self.context["user"]

        ride_request = RideRequestService.reject_request(
            request_id=request_id, user=user
        )

        return {
            "request": ride_request,
            "detail": "Request rejected successfully",
        }


class CancelRideRequestSerializer(serializers.Serializer):

    def save(self, **kwargs):
        request_id = self.context["request_id"]
        user = self.context["user"]

        ride_request = RideRequestService.cancel_request(
            request_id=request_id, user=user
        )

        return {
            "request": ride_request,
            "detail": "Request cancelled successfully",
        }
