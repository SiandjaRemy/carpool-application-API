import uuid

from django.db import transaction
from django.utils import timezone
from carpool.models import RideRequest, Ride
from carpool.enums.enums import RequestStatus, ReservationStatus, RideStatus
from carpool.services.reservation_service import ReservationService


class RideRequestService:
    """Service layer for ride request business logic"""

    @staticmethod
    def _validate_request_creation(ride, passenger, request_data):
        """Validate reservation data before creation"""
        # Check if ride exists and is available
        if ride.status != RideStatus.SCHEDULED:
            raise ValueError("Cannot request seats for a ride that is not scheduled")

        if ride.fully_reserved:
            raise ValueError("This ride is fully reserved")

        # Check if user is trying to reserve their own ride (This is just an extra check tho)
        if ride.user == passenger:
            raise ValueError("You cannot reserve seats for a ride you created")

        # Check seat availability
        if request_data["seats_requested"] > ride.available_seats:
            if ride.available_seats == 0:
                raise ValueError("This ride is fully reserved")
            else:
                raise ValueError(
                    f"Only {ride.available_seats} seats are available for this ride"
                )

        if ride.requests.filter(
            passenger=passenger, status=RequestStatus.PENDING
        ).exists():
            raise ValueError(
                "You already have a reservation. Cancel it first if you wish to make a new request"
            )

    @staticmethod
    def _validate_request_update(instance, data):
        """Validate ride request update data"""
        # Can only update scheduled requests
        if instance.status != RequestStatus.PENDING:
            raise ValueError("This request cannot be updated.")

        # The checks bellow are extra checks and are optional
        # Check price if being updated
        if "price_per_seat" in data and data["price_per_seat"] < 0:
            raise ValueError("Price per seat must be positive")

        # Check seats if being updated
        if "seats_requested" in data:
            if data["seats_requested"] < 0:
                raise ValueError("Seats requested must be positive.")
            else:
                ride = instance.ride
                current_seats = instance.seats_requested

                # If increasing seats, check availability
                if data["seats_requested"] > current_seats:
                    additional_seats = data["seats_requested"] - current_seats
                    if ride.available_seats < data["seats_requested"]:
                        raise ValueError(
                            f"Cannot increase by {additional_seats}. Only {ride.available_seats} seats available."
                        )

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
    def create_request(cls, ride_id, passenger, request_data):
        """
        Create a new reservation for a ride
        """

        try:
            ride = Ride.objects.prefetch_related("requests").get(id=ride_id)
        except Ride.DoesNotExist:
            raise ValueError("Ride not found or you don't have permission")

        # Validate
        cls._validate_request_creation(ride, passenger, request_data)

        request_data["ride"] = ride
        request_data["passenger"] = passenger

        try:
            # Create ride_request
            ride_request = RideRequest.objects.create(**request_data)

            # Trigger notifications
            # from carpool.tasks import send_ride_request_confirmation
            # transaction.on_commit(
            #     lambda: send_ride_request_confirmation.delay(ride_request.id)
            # )

            return ride_request

        except Exception as e:
            raise ValueError(f"Failed to create request: {str(e)}")

    @classmethod
    @transaction.atomic
    def update_request(cls, update_data, instance, passenger):
        """
        Update an existing ride request
        """
        if instance.passenger != passenger:
            raise ValueError("Ride not found or you don't have permission")

        # Validate update
        cls._validate_request_update(instance, update_data)

        # Update fields
        for field, value in update_data.items():
            setattr(instance, field, value)

        instance.save(update_fields=list(update_data.keys()) + ["updated_at"])

        return instance

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
        if request.seats_requested > ride.available_seats:
            raise ValueError(
                f"Not enough seats. Only {ride.available_seats} available."
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
