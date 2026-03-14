import uuid

from django.db import models
from django.contrib.auth import get_user_model

from carpool.models.base import TimeStampedModel

User = get_user_model()


class RideAlert(TimeStampedModel):
    id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True, unique=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ride_alerts")
    departure_town = models.CharField(max_length=255)
    arrival_town = models.CharField(max_length=255)
    before_date = models.DateTimeField(null=True, blank=True)
    after_date = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["departure_town", "arrival_town"]),
            models.Index(fields=["is_active"]),
        ]
