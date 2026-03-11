import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

from carpool.enums.enums import RequestStatus
from carpool.models.base import TimeStampedModel
from carpool.models.ride import Ride

User = get_user_model()


class RideRequest(TimeStampedModel):
    id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True, unique=True
    )
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="requests")
    passenger = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ride_requests"
    )
    status = models.CharField(
        max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING
    )
    seats_requested = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    price_per_seat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1)],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["ride", "passenger", "status"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["ride", "status"]),
        ]
