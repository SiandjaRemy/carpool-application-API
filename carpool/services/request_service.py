import uuid

from django.db import transaction
from django.utils import timezone
from carpool.exceptions import (
    BusinessValidationError,
    ResourcePermissionError,
)
from carpool.models import RideRequest, Ride
from carpool.enums.enums import RequestStatus, RideStatus
from carpool.services.reservation_service import ReservationService


class RideRequestService:
    """Service layer for ride request business logic"""

    @staticmethod
    def _validate_request_state(request: RideRequest):
        """
        Unified validator for RideRequest state.
        Checks both the request data and the parent ride's current status.
        """
        ride = request.ride

        # Parent Ride Status Checks
        if ride.status != RideStatus.SCHEDULED:
            raise BusinessValidationError(
                "Cannot request seats for a ride that is not scheduled."
            )

        if ride.departure_datetime <= timezone.now():
            raise BusinessValidationError("This ride has already departed.")

        if ride.fully_reserved:
            raise BusinessValidationError("This ride is already fully reserved.")

        # Relationship Checks
        if ride.user == request.passenger:
            raise BusinessValidationError(
                "You cannot reserve seats for a ride you created."
            )

        # Seat Availability
        if ride.available_seats < 1:
            raise BusinessValidationError("Fully reserved.")

        if request.seats_requested < 1:
            raise BusinessValidationError("You must request at least 1 seat.")

        if request.seats_requested > ride.available_seats:
            raise BusinessValidationError(
                f"Only {ride.available_seats} seats are available for this ride."
            )

        # Duplicate Check (Exclude current request if updating)
        existing_pending = RideRequest.objects.filter(
            ride=ride, passenger=request.passenger, status=RequestStatus.PENDING
        ).exclude(pk=request.pk)

        if existing_pending.exists():
            raise BusinessValidationError(
                "You already have a pending request for this ride."
            )

    @staticmethod
    def _validate_modification_permission(ride_request, user, role):
        """Check if the user has the correct role to modify this specific request."""
        if ride_request.status != RequestStatus.PENDING:
            raise BusinessValidationError("Only pending requests can be modified.")

        if ride_request.ride.departure_datetime <= timezone.now():
            raise BusinessValidationError("Ride has already departed")

        if role == "owner" and ride_request.ride.user != user:
            raise ResourcePermissionError(
                "Only the ride owner can perform this action."
            )

        if role == "passenger" and ride_request.passenger != user:
            raise ResourcePermissionError("Only the passenger can perform this action.")

    @classmethod
    @transaction.atomic
    def create_request(cls, ride_id, passenger, request_data):
        # Fetch Ride (Handler returns 404 if not found)
        ride = Ride.objects.get(id=ride_id)

        # Instantiate request in memory
        ride_request = RideRequest(**request_data, ride=ride, passenger=passenger)

        # Validate unified state
        cls._validate_request_state(ride_request)

        ride_request.save()
        return ride_request

    @classmethod
    @transaction.atomic
    def update_request(cls, request_id, update_data, passenger):
        # Fetch and Lock
        request = RideRequest.objects.select_for_update().get(
            id=request_id, passenger=passenger
        )

        # 3. Validate modification status
        cls._validate_modification_permission(request, passenger, "passenger")

        # Apply changes in memory
        for field, value in update_data.items():
            setattr(request, field, value)

        # Re-validate state
        cls._validate_request_state(request)

        request.save(update_fields=list(update_data.keys()) + ["updated_at"])
        return request

    @classmethod
    @transaction.atomic
    def accept_request(cls, request_id: uuid.UUID, user):
        # 1. Fetch and Lock the Request
        # Note: We filter by ride__user=user to handle 404/403 context immediately
        request = RideRequest.objects.select_for_update().get(
            id=request_id, ride__user=user
        )

        # 2. Lock the Ride itself (Crucial to prevent seat-overbooking race conditions)
        ride = Ride.objects.get(id=request.ride.id)

        # 3. Validate modification status
        cls._validate_modification_permission(request, user, "owner")

        # 4. Final Seat Check (The "Just-in-Time" check)
        if request.seats_requested > ride.available_seats:
            raise BusinessValidationError(
                f"Not enough seats available ({ride.available_seats})."
            )

        # 5. Update Status
        request.status = RequestStatus.ACCEPTED
        request.is_active = False
        request.save(update_fields=["status", "is_active", "updated_at"])

        # 6. Call Reservation Logic
        ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=request.passenger,
            seats_requested=request.seats_requested,
            price_per_seat=ride.price_per_seat,
        )

        return request

    @classmethod
    @transaction.atomic
    def reject_request(cls, request_id: uuid.UUID, user):
        request = RideRequest.objects.select_for_update().get(
            id=request_id, ride__user=user
        )

        cls._validate_modification_permission(request, user, "owner")

        request.status = RequestStatus.REJECTED
        request.is_active = False
        request.save(update_fields=["status", "is_active", "updated_at"])
        return request

    @classmethod
    @transaction.atomic
    def cancel_request(cls, request_id: uuid.UUID, user):
        request = RideRequest.objects.select_for_update().get(
            id=request_id, passenger=user
        )

        cls._validate_modification_permission(request, user, "passenger")

        request.status = RequestStatus.CANCELLED
        request.is_active = False
        request.save(update_fields=["status", "is_active", "updated_at"])
        return request

    @classmethod
    @transaction.atomic
    def cancel_ride_requests(cls, ride_id):
        """Bulk update for system-level ride cancellation"""
        requests = RideRequest.objects.filter(ride_id=ride_id)

        if not requests.exists():
            return "No requests to update."

        # Handle those already accepted vs those still pending
        updated_count = requests.filter(status=RequestStatus.ACCEPTED).update(
            status=RequestStatus.DRIVER_CANCELLED, updated_at=timezone.now()
        )

        ReservationService.cancel_ride_reservations(ride_id=ride_id)
        return f"{updated_count} accepted requests moved to DRIVER_CANCELLED."

    @classmethod
    @transaction.atomic
    def toggle_request(cls, request_id: uuid.UUID, user):
        """
        Toggle request active status
        """
        request = RideRequest.objects.select_for_update().get(
            id=request_id, passenger=user
        )

        request.is_active = not request.is_active
        request.save(update_fields=["is_active", "updated_at"])

        return request
