from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator

from core.models import TimeStampedModel

User = get_user_model()


class Reservations(TimeStampedModel):
    id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True, unique=True
    )
    user = models.ForeignKey(
        User, related_name="reservations", on_delete=models.CASCADE
    )
    ride = models.ForeignKey(
        "rides.Ride", related_name="reservations", on_delete=models.CASCADE
    )
    number_of_seats = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )

    def __str__(self):
        return f"{self.user} booked {self.number_of_seats} - ({self.ride})"
