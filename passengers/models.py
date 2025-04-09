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


class Passenger(TimeStampedModel):
    id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True, unique=True
    )
    user = models.ForeignKey(User, related_name="seats", on_delete=models.CASCADE)
    ride = models.ForeignKey("rides.Ride", related_name="passengers", on_delete=models.CASCADE)
    number_of_seats = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    def __str__(self):
        return f"{self.user} booked {self.number_of_seats} - ({self.ride})"
    

    