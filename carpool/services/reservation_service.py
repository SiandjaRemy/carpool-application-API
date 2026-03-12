from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum, Count

from carpool.models import Reservation, Ride
from carpool.enums.enums import ReservationPaymentStatus, RideStatus


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

        # Check if ride hasn't departed yet
        if reservation.ride.departure_datetime <= timezone.now():
            raise ValueError(
                "Cannot cancel reservation for a ride that has already departed"
            )

        # Check cancellation timeframe (e.g., 2 hours before departure)
        time_until_departure = reservation.ride.departure_datetime - timezone.now()
        if time_until_departure < timedelta(hours=2):
            raise ValueError(
                "Cannot cancel reservation less than 2 hours before departure. "
                "Please contact the driver directly."
            )

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

        # Update reservation status
        reservation.payment_status = ReservationPaymentStatus.REFUNDED
        reservation.save(update_fields=["status", "updated_at"])

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
            total_reservations=Sum("seats_requested"),
            passenger_count=Count("id"),
            cancelled_count=Count("id", filter=Q(status="cancelled")),
        )

        return {
            "total_seats_reserved": stats["total_reservations"] or 0,
            "passenger_count": stats["passenger_count"] or 0,
            "cancelled_count": stats["cancelled_count"] or 0,
            "available_seats": ride.available_seats,
            "is_fully_reserved": ride.fully_reserved,
        }
