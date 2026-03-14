import uuid

from django.db import transaction
from django.utils import timezone
from carpool.models import RideRequest, Ride
from carpool.enums.enums import RequestStatus
from carpool.services.reservation_service import ReservationService


class RideRequestService:
    """Service layer for ride request business logic"""

    @staticmethod
    def _validate_request_modification(request, user, allowed_roles):
        """Single source of truth for validation"""
        if request.status != RequestStatus.PENDING:
            raise ValueError("Only pending requests can be modified")

        if request.ride.departure_datetime <= timezone.now():
            raise ValueError("Ride has already departed")

        # Role-based checks
        if "owner" in allowed_roles and request.ride.user != user:
            raise PermissionError("Only ride owner can perform this action")

        if "passenger" in allowed_roles and request.passenger != user:
            raise PermissionError("Only passenger can perform this action")

    @classmethod
    @transaction.atomic
    def accept_request(cls, request_id: uuid.UUID, user):
        """Accept a ride request with all business rules"""
        # Complex acceptance logic here
        try:
            request = (
                RideRequest.objects.select_for_update()
                .select_related("ride")
                .get(id=request_id, ride__user=user)
            )

            ride = Ride.objects.select_for_update().get(id=request.ride.id)
        except RideRequest.DoesNotExist:
            raise ValueError("Ride request not found or you don't have permission")

        cls._validate_request_modification(request, user, ["owner"])

        # Extra Validation
        if request.seats_requested > request.ride.available_seats:
            raise ValueError(
                f"Not enough seats. Only {request.ride.available_seats} available."
            )

        # Business logic
        request.status = RequestStatus.ACCEPTED
        request.is_active = False
        request.save(update_fields=["status", "is_active", "updated_at"])

        # Create reservation using ReservationService
        ReservationService.create_reservation(
            ride=ride,
            passenger=request.passenger,
            seats_requested=request.seats_requested,
            price_per_seat=request.ride.price_per_seat,
        )

        # # Trigger notifications
        # from carpool.tasks import send_request_accepted_notification

        # transaction.on_commit(
        #     lambda: send_request_accepted_notification.delay(request.id)
        # )

        return request

    @classmethod
    @transaction.atomic
    def reject_request(cls, request_id: uuid.UUID, user):
        """Reject a ride request with all business rules"""
        # Complex reject logic here
        try:
            request = (
                RideRequest.objects.select_for_update()
                .select_related("ride")
                .get(id=request_id, ride__user=user)
            )
        except RideRequest.DoesNotExist:
            raise ValueError("Ride request not found or you don't have permission")

        cls._validate_request_modification(request, user, ["owner"])

        # Business logic
        request.status = RequestStatus.REJECTED
        request.is_active = False
        request.save(update_fields=["status", "is_active", "updated_at"])

        # # Trigger notifications
        # from carpool.tasks import send_request_rejected_notification

        # transaction.on_commit(
        #     lambda: send_request_rejected_notification.delay(request.id)
        # )

        return request

    @classmethod
    @transaction.atomic
    def cancel_request(cls, request_id: uuid.UUID, user):
        """Cancel a ride request with all business rules"""
        # Complex cancelation logic here
        try:
            request = (
                RideRequest.objects.select_for_update()
                .select_related("ride")
                .get(id=request_id, passenger=user)
            )
        except RideRequest.DoesNotExist:
            raise ValueError("Ride request not found or you don't have permission")

        cls._validate_request_modification(request, user, ["passenger"])

        # Business logic
        request.status = RequestStatus.CANCELLED
        request.is_active = False
        request.save(update_fields=["status", "is_active", "updated_at"])

        return request

    @classmethod
    @transaction.atomic
    def cancel_ride_requests(cls, ride_id):
        """
        Cancel all requests for a ride in bulk
        """
        # Get all requests for the ride
        requests = RideRequest.objects.filter(ride_id=ride_id)

        if not requests.exists():
            return requests.none()  # Return empty queryset

        # Update the status of the accepted request
        accepted_request = requests.filter(
            ride_id=ride_id, status=RequestStatus.ACCEPTED
        ).update(
            status=RequestStatus.DRIVER_CANCELLED,
        )

        # Auto cancel all reservations "appropriatly" if they exist
        ReservationService.cancel_ride_reservations(ride_id=ride_id)

        return "Done"

    @classmethod
    @transaction.atomic
    def toggle_request(cls, request_id: uuid.UUID, user):
        """
        Toggle request active status
        """
        try:
            request = RideRequest.objects.select_for_update().get(
                id=request_id, passenger=user
            )
        except RideRequest.DoesNotExist:
            raise ValueError("Ride request not found")

        request.is_active = not request.is_active
        request.save(update_fields=["is_active", "updated_at"])

        return request
