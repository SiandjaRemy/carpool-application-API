from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from carpool.models import Ride
from carpool.enums.enums import RideStatus
from carpool.services.request_service import RideRequestService


class RideService:
    """Service layer for ride business logic"""

    @staticmethod
    def _validate_ride_creation(ride_data, user):
        """Validate ride data before creation"""
        # Ensure departure time is in the future
        if ride_data.get("departure_datetime") <= timezone.now():
            raise ValueError("Departure time must be in the future")

        # Ensure seats are positive
        if ride_data.get("available_seats", 0) < 0:
            raise ValueError("You must have at least 1 free seat")

        # Ensure price is positive
        if ride_data.get("price_per_seat", 0) < 0:
            raise ValueError("You must set a price per seat")

        # Check if user has any conflicting rides (optional)
        conflicting_rides = Ride.objects.filter(
            user=user,
            status=RideStatus.SCHEDULED,
            departure_datetime__range=(
                ride_data["departure_datetime"] - timedelta(hours=2),
                ride_data["departure_datetime"] + timedelta(hours=2),
            ),
        ).exists()

        if conflicting_rides:
            raise ValueError("You already have a ride scheduled around this time")

    @staticmethod
    def _validate_ride_update(ride, data):
        """Validate ride update data"""
        # Can only update scheduled rides
        if ride.status != RideStatus.SCHEDULED:
            raise ValueError("Only scheduled rides can be updated")

        # Check departure time if being updated
        if "departure_datetime" in data:
            if data["departure_datetime"] <= timezone.now():
                raise ValueError("Departure time must be in the future")

        # Check seats if being updated
        if "available_seats" in data:
            if data["available_seats"] < 0:
                raise ValueError("Available seats cannot be negative")

        # Check price if being updated
        if "price_per_seat" in data and data["price_per_seat"] < 0:
            raise ValueError("You must set a price per seat")

    @staticmethod
    def _validate_ride_cancelation(ride, user):
        """Validate ride update data"""
        # Can only update scheduled rides
        if ride.user != user:
            raise ValueError("Only scheduled rides can be updated")

    @classmethod
    @transaction.atomic
    def create_ride(cls, ride_data, user):
        """
        Create a new ride with validation
        """
        # Add user to data
        ride_data["user"] = user

        # Validate
        cls._validate_ride_creation(ride_data, user)

        try:
            # Create the ride
            ride = Ride.objects.create(**ride_data)

            # Trigger any background tasks
            # from carpool.tasks import notify_users_about_new_ride
            # transaction.on_commit(
            #     lambda: notify_users_about_new_ride.delay(ride.id)
            # )

            return ride
        except Exception as e:
            raise ValueError(f"Failed to create ride: {str(e)}")

    @classmethod
    @transaction.atomic
    def update_ride(cls, update_data, instance, user):
        """
        Update an existing ride
        """
        if instance.user != user:
            raise ValueError("Ride not found or you don't have permission")

        # Validate update
        cls._validate_ride_update(instance, update_data)

        # Update fields
        for field, value in update_data.items():
            setattr(instance, field, value)

        instance.save(update_fields=list(update_data.keys()) + ["updated_at"])

        return instance

    @classmethod
    @transaction.atomic
    def cancel_ride(cls, ride_id, user):
        """
        Cancel a scheduled ride
        """
        try:
            ride = (
                Ride.objects.select_for_update()
                .select_related("user")
                .get(id=ride_id, user=user, status=RideStatus.SCHEDULED)
            )
        except Ride.DoesNotExist:
            raise ValueError("Scheduled ride not found or you don't have permission")

        # Validate cancelation
        cls._validate_ride_cancelation(ride, user)

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
