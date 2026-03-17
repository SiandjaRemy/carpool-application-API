from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum, Count, When, Case, Value, F
from django.db.models.fields import CharField

from carpool.models import Reservation, Ride
from carpool.enums.enums import ReservationPaymentStatus, RideStatus, ReservationStatus


class ReservationService:
    """Service layer for reservation business logic"""

    @staticmethod
    def _validate_reservation_creation(ride, user, seats_requested):
        """Validate reservation data before creation"""
        # Check if ride exists and is available
        if ride.status != RideStatus.SCHEDULED:
            raise ValueError("Cannot reserve seats for a ride that is not scheduled")

        if ride.fully_reserved:
            raise ValueError("This ride is fully reserved")

        # Check if user is trying to reserve their own ride (This is just an extra check tho)
        if ride.user == user:
            raise ValueError("You cannot reserve seats for a ride you created")

        # Check seat availability
        if seats_requested > ride.available_seats:
            raise ValueError(
                f"Only {ride.available_seats} seats available, "
                f"but you requested {seats_requested}"
            )

        # Reservations are not created manually,
        # so we can limit the validation to these

    @staticmethod
    def _validate_reservation_cancellation(reservation, passenger):
        """Validate if a reservation can be cancelled"""

        # Check if reservation belongs to passenger
        if reservation.passenger != passenger:
            raise PermissionError("You can only cancel your own reservations")

        if reservation.status == ReservationStatus.CANCELLED:
            raise ValueError("This reservation is already cancelled")

        if reservation.payment_status == ReservationPaymentStatus.PAID:
            # Check if ride hasn't departed yet
            if reservation.ride.departure_datetime <= timezone.now():
                raise ValueError(
                    "Cannot cancel paid reservation for a ride that has already departed"
                )

            # Check cancellation timeframe (e.g., 2 hours before departure)
            time_until_departure = reservation.ride.departure_datetime - timezone.now()
            if time_until_departure < timedelta(hours=2):
                raise ValueError(
                    "Cannot cancel paid reservation less than 2 hours before departure. "
                    "Please contact the driver directly."
                )

        elif reservation.payment_status in [
            ReservationPaymentStatus.PENDING,
            ReservationPaymentStatus.FAILED,
        ]:
            # Check if ride hasn't departed yet
            if reservation.ride.departure_datetime <= timezone.now():
                raise ValueError("This reservation will be cancelled automatically")

    @staticmethod
    def _validate_reservation_payment(reservation, passenger):
        """Validate if a reservation can be cancelled"""

        # Check if reservation belongs to passenger
        if reservation.passenger != passenger:
            raise PermissionError("You can only pay for your own reservations")

        if reservation.status == ReservationStatus.CANCELLED:
            raise ValueError("You cant pay for cancelled reservations")

        if reservation.status == ReservationStatus.CONFIRMED:
            raise ValueError("You have already paid for this reservations")

        # Check if ride hasn't departed yet
        if reservation.ride.departure_datetime <= timezone.now():
            raise ValueError("Too late, ride has started")

    @classmethod
    @transaction.atomic
    def create_reservation(cls, ride, passenger, seats_requested, price_per_seat):
        """
        Create a new reservation for a ride
        """

        # Validate
        cls._validate_reservation_creation(ride, passenger, seats_requested)

        try:
            # Create reservation
            reservation = Reservation.objects.create(
                ride=ride,
                passenger=passenger,
                seats_requested=seats_requested,
                price_per_seat=price_per_seat,
            )

            # Update ride available seats
            ride.available_seats -= seats_requested
            if ride.available_seats == 0:
                ride.fully_reserved = True
            ride.save(update_fields=["available_seats", "fully_reserved", "updated_at"])

            # Trigger notifications
            # from carpool.tasks import send_reservation_confirmation
            # transaction.on_commit(
            #     lambda: send_reservation_confirmation.delay(reservation.id)
            # )

            return reservation

        except Exception as e:
            raise ValueError(f"Failed to create reservation: {str(e)}")

    @classmethod
    @transaction.atomic
    def cancel_reservation(cls, reservation_id, passenger):
        """
        Cancel an existing reservation and free up seats
        """
        try:
            reservation = (
                Reservation.objects.select_for_update()
                .select_related("ride")
                .get(id=reservation_id)
            )
        except Reservation.DoesNotExist:
            raise ValueError("Reservation not found")

        # Validate cancellation
        cls._validate_reservation_cancellation(reservation, passenger)

        # Lock the ride
        ride = Ride.objects.select_for_update().get(id=reservation.ride.id)

        # Update reservation status conditionally
        if reservation.payment_status in [
            ReservationPaymentStatus.PENDING,
            ReservationPaymentStatus.FAILED,
        ]:
            reservation.payment_status = ReservationPaymentStatus.PAYMENT_DISABLED
            reservation.status = ReservationStatus.CANCELLED
        elif reservation.payment_status == ReservationPaymentStatus.PAID:
            # Trigger refund logic
            reservation.payment_status = ReservationPaymentStatus.REFUNDED
            reservation.status = ReservationStatus.CANCELLED

        reservation.save(update_fields=["status", "payment_status", "updated_at"])

        # Return seats to the ride
        ride.available_seats += reservation.seats_requested
        ride.fully_reserved = False
        ride.save(update_fields=["available_seats", "fully_reserved", "updated_at"])

        # Notify driver (optional)
        # from carpool.tasks import notify_reservation_cancelled
        # transaction.on_commit(
        #     lambda: notify_reservation_cancelled.delay(reservation.id)
        # )

        return reservation

    @classmethod
    @transaction.atomic
    def pay_reservation(cls, reservation_id, passenger, payment_method="stripe"):
        """
        Process payment for a reservation.

        Args:
            reservation_id: UUID of the reservation
            passenger: User object making the payment
            payment_method: Payment method details

        Returns:
            Updated reservation object

        The reservation status remains PENDING until payment succeeds.
        If payment fails, payment_status becomes FAILED but status stays PENDING
        allowing the user to retry.
        """
        try:
            reservation = (
                Reservation.objects.select_for_update()
                .select_related("ride")
                .get(id=reservation_id)
            )
        except Reservation.DoesNotExist:
            raise ValueError("Reservation not found")

        # Validate the reservation can be paid
        cls._validate_reservation_payment(reservation, passenger)
        # Process the payment
        try:
            # Simulate payment processing - replace with actual payment gateway
            payment_successful = cls._process_payment(reservation, payment_method)

            if payment_successful:
                # Payment succeeded
                reservation.payment_status = ReservationPaymentStatus.PAID
                reservation.status = ReservationStatus.CONFIRMED
                reservation.confirmed_at = timezone.now()

                # Optionally send confirmation
                # from carpool.tasks import send_payment_confirmation
                # transaction.on_commit(
                #     lambda: send_payment_confirmation.delay(reservation.id)
                # )
            else:
                # Payment failed - keep status PENDING for retry
                reservation.payment_status = ReservationPaymentStatus.FAILED
                # status remains PENDING - user can retry

        except Exception as e:
            # Unexpected error during payment processing
            reservation.payment_status = ReservationPaymentStatus.FAILED
            # Log the error for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Payment processing error for reservation {reservation_id}: {str(e)}"
            )
            raise ValueError(f"Payment processing failed: {str(e)}")

        # Save changes
        reservation.save(
            update_fields=["status", "payment_status", "confirmed_at", "updated_at"]
        )

        return reservation

    @staticmethod
    def _process_payment(reservation, payment_method=None):
        """
        Simulate payment processing.
        Replace this with actual payment gateway integration.

        Returns:
            bool: True if payment succeeded, False otherwise
        """
        # Add payment logic here
        # This is just a demo projec so for now i'll always return true
        return True

    @classmethod
    @transaction.atomic
    def cancel_ride_reservations(cls, ride_id):
        """
        Cancel all reservations for a ride in bulk
        """
        # Get all reservations for the ride
        reservations = Reservation.objects.filter(ride_id=ride_id)

        if not reservations.exists():
            return reservations.none()  # Return empty queryset

        # Perform bulk update with conditional logic
        updated_count = reservations.select_for_update().update(
            payment_status=Case(
                When(
                    payment_status=ReservationPaymentStatus.PAID,
                    then=Value(ReservationPaymentStatus.REFUNDED),
                ),
                When(
                    payment_status__in=[
                        ReservationPaymentStatus.PENDING,
                        ReservationPaymentStatus.FAILED,
                    ],
                    then=Value(ReservationPaymentStatus.PAYMENT_DISABLED),
                ),
                default=F("payment_status"),
                output_field=CharField(),
            ),
            status=ReservationStatus.CANCELLED,
        )

        return "Done"

    @classmethod
    def get_reservation_stats(cls, ride_id, user):
        """
        Get statistics about reservations for a ride (for ride owner)
        """
        try:
            ride = Ride.objects.get(id=ride_id)
        except Ride.DoesNotExist:
            raise ValueError("Ride not found")

        if ride.user != user:
            raise PermissionError("Only the ride owner can view reservation statistics")

        stats = Reservation.objects.filter(ride=ride).aggregate(
            paid_reservations=Count(
                "id",
                filter=Q(status=ReservationStatus.CONFIRMED),
            ),
            pending_reservations=Count(
                "id",
                filter=Q(status=ReservationStatus.PENDING),
            ),
            total_paid_seats=Sum(
                "seats_requested", filter=Q(status=ReservationStatus.CONFIRMED)
            ),
            total_unpaid_seats=Sum(
                "seats_requested",
                filter=Q(status=ReservationStatus.PENDING),
            ),
            cancelled_count=Count("id", filter=Q(status=ReservationStatus.CANCELLED)),
        )

        return {
            "paid_reservations": stats["paid_reservations"] or 0,
            "total_paid_seats": stats["total_paid_seats"] or 0,
            "pending_reservations": stats["pending_reservations"] or 0,
            "total_unpaid_seats": stats["total_unpaid_seats"] or 0,
            "cancelled_count": stats["cancelled_count"] or 0,
            "available_seats": ride.available_seats,
            "is_fully_reserved": ride.fully_reserved,
        }
