import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

from carpool.enums.enums import RideStatus
from carpool.models.base import TimeStampedModel


User = get_user_model()


class Ride(TimeStampedModel):
    id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True, unique=True
    )
    user = models.ForeignKey(User, related_name="rides", on_delete=models.CASCADE)
    departure_town = models.CharField(max_length=100)
    arrival_town = models.CharField(max_length=100)
    departure_datetime = models.DateTimeField()
    # This is set after the ride completion
    arrival_datetime = models.DateTimeField(blank=True, null=True)

    available_seats = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ]
    )
    price_per_seat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1)],
    )
    status = models.CharField(
        max_length=20, choices=RideStatus.choices, default=RideStatus.SCHEDULED
    )
    fully_reserved = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)

    @property
    def seats_available(self):
        return not self.fully_reserved

    def __str__(self):
        date_time = self.departure_datetime.strftime("%Y-%m-%d - %H:%M:%S")
        return f"{self.user} will ride from {self.departure_town} to {self.arrival_town} on {date_time}"

    class Meta:
        indexes = [
            models.Index(fields=["departure_datetime"]),
            models.Index(fields=["departure_town", "arrival_town"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            # Ensures available_seats is always between 1 and 10 at the DB level
            models.CheckConstraint(
                condition=models.Q(available_seats__gte=0)
                & models.Q(available_seats__lte=10),
                name="available_seats_range",
            ),
            # Ensures price is never zero or negative
            models.CheckConstraint(
                condition=models.Q(price_per_seat__gte=1), name="price_positive"
            ),
        ]
