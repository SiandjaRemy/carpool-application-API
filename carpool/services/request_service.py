# carpool/services/request_service.py
import uuid

from django.db import transaction
from django.utils import timezone
from carpool.models import RideRequest, Ride, Reservation
from carpool.enums.enums import RequestStatus, RideStatus


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

        request.ride.available_seats -= request.seats_requested
        request.ride.save(update_fields=["available_seats", "updated_at"])

        # Create reservation
        Reservation.objects.create(
            ride=request.ride,
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
