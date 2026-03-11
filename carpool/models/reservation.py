import uuid

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

from carpool.enums.enums import ReservationPaymentStatus
from carpool.models.base import TimeStampedModel
from carpool.models.ride import Ride

User = get_user_model()


class Reservation(TimeStampedModel):
    id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True, unique=True
    )
    ride = models.ForeignKey(
        Ride, on_delete=models.CASCADE, related_name="reservations"
    )
    passenger = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reservations"
    )
    payment_status = models.CharField(
        max_length=20,
        choices=ReservationPaymentStatus.choices,
        default=ReservationPaymentStatus.PENDING,
    )
    seats_requested = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    price_per_seat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1)],
    )

    confirmed_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_confirmed(self):
        """Returns True if the reservation was confirmes by the passenger."""
        return self.confirmed_at is not None

    class Meta:
        indexes = [
            models.Index(fields=["payment_status"]),
        ]
