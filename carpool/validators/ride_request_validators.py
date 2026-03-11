from rest_framework import serializers

from carpool.enums.enums import RequestStatus
from carpool.models import RideRequest


def validate_ride_request_exists(ride_id, user):
    """Ensure that the user is not having a pending/accepted request for a particular ride"""
    exists = RideRequest.objects.filter(
        ride__id=ride_id,
        passenger=user,
        status__in=[RequestStatus.PENDING, RequestStatus.ACCEPTED],
    ).exists()
    if exists:
        raise serializers.ValidationError(
            {"message": "You already made a request for this ride."}
        )
