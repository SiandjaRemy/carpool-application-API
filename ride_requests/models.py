from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator

from utils.validators import validate_number_of_seats_greater_then_zero

User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


    
class RideRequest(TimeStampedModel):
    id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True, unique=True
    )
    user = models.ForeignKey(User, related_name="ride_requests", on_delete=models.CASCADE)
    departure_town = models.CharField(max_length=100)
    arrival_town = models.CharField(max_length=100)
    departure_datetime = models.DateTimeField()
    required_seats = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    price_per_seat = models.FloatField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        date_time = self.departure_datetime.strftime("%Y-%m-%d - %H:%M:%S")
        return f"{self.user} needs a ride from {self.departure_town} to {self.arrival_town} on {date_time}"


