from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from carpool.exceptions import (
    BusinessValidationError,
    ResourceNotFoundError,
    ResourcePermissionError,
)
from carpool.models import Ride
from carpool.enums.enums import RideStatus
from carpool.services.request_service import RideRequestService


class RideService:
    """Service layer for ride business logic"""

    @staticmethod
    def _validate_ride_state(ride):
        """
        Validates the overall state of a Ride object,
        whether newly created or recently updated.
        """
        if ride.status != RideStatus.SCHEDULED:
            raise BusinessValidationError(f"Cannot modify a ride that is {ride.status}")

        if ride.departure_datetime <= timezone.now():
            raise BusinessValidationError("Departure time must be in the future")

        if ride.available_seats <= 0:
            raise BusinessValidationError("A ride must have at least 1 available seat")

        if ride.price_per_seat < 0:
            raise BusinessValidationError("Price per seat cannot be negative")

        query = Ride.objects.filter(
            user=ride.user,
            status=RideStatus.SCHEDULED,
            departure_datetime__range=(
                ride.departure_datetime - timedelta(hours=2),
                ride.departure_datetime + timedelta(hours=2),
            ),
        )

        if ride.pk:
            query = query.exclude(pk=ride.pk)

        if query.exists():
            raise BusinessValidationError("Schedule conflict detected.")

    @classmethod
    @transaction.atomic
    def create_ride(cls, ride_data, user):
        # Create instance in memory only (does not hit DB yet)
        ride = Ride(**ride_data, user=user)

        # Validate the state of this new object
        cls._validate_ride_state(ride)

        # Now save to DB
        ride.save()
        return ride

    @classmethod
    @transaction.atomic
    def update_ride(cls, ride_id, update_data, user):
        """
        Update an existing ride with row-level locking.
        """

        # 1. Fetch and Lock the ride
        instance = Ride.objects.select_for_update().get(id=ride_id, user=user)

        # Apply updates to the instance in memory
        for field, value in update_data.items():
            setattr(instance, field, value)

        # Validate the FINAL state of the object
        cls._validate_ride_state(instance)

        # Save
        instance.save(update_fields=list(update_data.keys()) + ["updated_at"])

        return instance

    @classmethod
    @transaction.atomic
    def cancel_ride(cls, ride_id, user):
        """
        Cancel a scheduled ride
        """
        ride = (
            Ride.objects.select_for_update()
            .select_related("user")
            .get(id=ride_id, status=RideStatus.SCHEDULED)
        )

        # Specific Permission Error
        if ride.user != user:
            raise ResourcePermissionError(
                "You do not have permission to cancel this ride."
            )

        # Auto cancel all ride requests if they exist
        RideRequestService.cancel_ride_requests(ride_id=ride_id)

        ride.status = RideStatus.CANCELLED
        ride.save(update_fields=["status", "updated_at"])

        # Notify passengers (if any)
        # from carpool.tasks import notify_ride_cancelled
        # transaction.on_commit(
        #     lambda: notify_ride_cancelled.delay(ride.id)
        # )

        return ride

    @classmethod
    def check_seat_availability(cls, ride_id, requested_seats):
        """
        Check if requested seats are available
        """
        try:
            ride = Ride.objects.get(id=ride_id)
            return ride.available_seats >= requested_seats
        except Ride.DoesNotExist:
            return False
