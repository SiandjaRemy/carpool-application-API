import pytest

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from datetime import timedelta
from decimal import Decimal

from carpool.exceptions import BusinessValidationError, ResourcePermissionError
from carpool.services.reservation_service import ReservationService
from carpool.enums.enums import RideStatus, ReservationPaymentStatus
from carpool.tests.factories import (
    UserFactory,
    RideFactory,
    ReservationFactory,
)

pytestmark = pytest.mark.unit


class TestReservationService:
    """Unit tests for reservation service"""

    # ----------------------------------------------------------------------
    # Create Reservation Tests
    # ----------------------------------------------------------------------

    def test_create_reservation_happy_path(self, db):
        """Test creating a reservation successfully"""
        passenger = UserFactory()
        ride = RideFactory(available_seats=4, price_per_seat=Decimal("30.50"))

        reservation = ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=passenger,
            seats_requested=2,
            price_per_seat=ride.price_per_seat,
        )

        assert reservation.id is not None
        assert reservation.passenger == passenger
        assert reservation.ride == ride
        assert reservation.seats_requested == 2
        assert reservation.price_per_seat == Decimal("30.50")
        assert reservation.payment_status == ReservationPaymentStatus.PENDING

        # Verify ride seats updated
        ride.refresh_from_db()
        assert ride.available_seats == 2
        assert ride.fully_reserved is False

    def test_create_reservation_fills_ride(self, db):
        """Test creating a reservation that fills all seats"""
        passenger = UserFactory()
        ride = RideFactory(available_seats=2)

        ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=passenger,
            seats_requested=2,
            price_per_seat=ride.price_per_seat,
        )

        ride.refresh_from_db()
        assert ride.available_seats == 0
        assert ride.fully_reserved is True

    def test_create_reservation_ride_not_scheduled(self, db):
        """Test cannot create reservation for non-scheduled ride"""
        passenger = UserFactory()
        ride = RideFactory(status=RideStatus.CANCELLED, available_seats=4)

        with pytest.raises(
            BusinessValidationError,
            match="Cannot create reservation for a ride that is not scheduled",
        ):
            ReservationService.create_reservation(
                ride_id=ride.id,
                passenger=passenger,
                seats_requested=2,
                price_per_seat=ride.price_per_seat,
            )

    def test_create_reservation_fully_reserved_ride(self, db):
        """Test cannot create reservation for fully reserved ride"""
        passenger = UserFactory()
        ride = RideFactory(available_seats=0, fully_reserved=True)

        with pytest.raises(
            BusinessValidationError, match="This ride is already fully reserved"
        ):
            ReservationService.create_reservation(
                ride_id=ride.id,
                passenger=passenger,
                seats_requested=2,
                price_per_seat=ride.price_per_seat,
            )

    def test_create_reservation_insufficient_seats(self, db):
        """Test cannot create reservation requesting more seats than available"""
        passenger = UserFactory()
        ride = RideFactory(available_seats=2)

        with pytest.raises(
            BusinessValidationError, match="Only 2 seats are available for this ride"
        ):
            ReservationService.create_reservation(
                ride_id=ride.id,
                passenger=passenger,
                seats_requested=3,
                price_per_seat=ride.price_per_seat,
            )

    def test_create_reservation_own_ride(self, db):
        """Test driver cannot create reservation for their own ride"""
        driver = UserFactory()
        ride = RideFactory(user=driver, available_seats=4)

        with pytest.raises(
            BusinessValidationError,
            match="You cannot reserve seats for a ride you created",
        ):
            ReservationService.create_reservation(
                ride_id=ride.id,
                passenger=driver,
                seats_requested=2,
                price_per_seat=ride.price_per_seat,
            )

    # ----------------------------------------------------------------------
    # Cancel Reservation Tests
    # ----------------------------------------------------------------------

    def test_cancel_reservation_happy_path(self, db):
        """Test cancelling a reservation successfully"""
        passenger = UserFactory()
        ride = RideFactory(available_seats=4)

        reservation = ReservationFactory(
            ride=ride, passenger=passenger, seats_requested=2
        )
        ride.available_seats = 2
        ride.save()

        cancelled = ReservationService.cancel_reservation(
            reservation_id=reservation.id, passenger=passenger
        )

        assert cancelled.id == reservation.id
        assert cancelled.payment_status == ReservationPaymentStatus.PAYMENT_DISABLED

        # Verify seats returned to ride
        ride.refresh_from_db()
        assert ride.available_seats == 4
        assert ride.fully_reserved is False

    def test_cancel_reservation_wrong_user(self, db):
        """Test cannot cancel another user's reservation"""
        passenger = UserFactory()
        other_user = UserFactory()
        reservation = ReservationFactory(passenger=passenger)

        with pytest.raises(
            ResourcePermissionError, match="You can only cancel your own reservations"
        ):
            ReservationService.cancel_reservation(
                reservation_id=reservation.id, passenger=other_user
            )

    def test_cancel_paid_reservation_ride_departed(self, db, freezer):
        """Test cannot cancel paid reservation for departed ride"""
        passenger = UserFactory()
        now = timezone.now()
        freezer.move_to(now)

        # Create ride that departed 1 hour ago
        ride = RideFactory(departure_datetime=now - timedelta(hours=1))
        reservation = ReservationFactory(
            ride=ride, passenger=passenger, payment_status=ReservationPaymentStatus.PAID
        )

        with pytest.raises(BusinessValidationError, match="already departed"):
            ReservationService.cancel_reservation(
                reservation_id=reservation.id, passenger=passenger
            )

    def test_cancel_paid_reservation_too_close_to_departure(self, db, freezer):
        """Test cannot cancel paid reservation less than 2 hours before departure"""
        passenger = UserFactory()
        now = timezone.now()
        freezer.move_to(now)

        # Create ride departing in 1 hour
        ride = RideFactory(departure_datetime=now + timedelta(hours=1))
        reservation = ReservationFactory(
            ride=ride, passenger=passenger, payment_status=ReservationPaymentStatus.PAID
        )

        with pytest.raises(
            BusinessValidationError,
            match="Cannot cancel paid reservation less than 2 hours before departure",
        ):
            ReservationService.cancel_reservation(
                reservation_id=reservation.id, passenger=passenger
            )

    def test_cancel_reservation_not_found(self, db):
        """Test cancelling non-existent reservation"""
        passenger = UserFactory()

        with pytest.raises(ObjectDoesNotExist, match="matching query does not exist"):
            ReservationService.cancel_reservation(
                reservation_id="00000000-0000-0000-0000-000000000000",
                passenger=passenger,
            )

    # ----------------------------------------------------------------------
    # Pay for Reservation Tests
    # ----------------------------------------------------------------------

    def test_pay_reservation_happy_path(self, db):
        """Test payment for a reservation successfully"""
        passenger = UserFactory()
        ride = RideFactory(available_seats=4)

        reservation = ReservationFactory(
            ride=ride, passenger=passenger, seats_requested=2
        )
        ride.available_seats = 2
        ride.save()

        pay = ReservationService.pay_reservation(
            reservation_id=reservation.id, passenger=passenger, payment_method="stripe"
        )

        assert pay.id == reservation.id
        assert pay.payment_status == ReservationPaymentStatus.PAID

        # Verify seats returned to ride
        ride.refresh_from_db()
        assert ride.available_seats == 2
        assert ride.reservations.filter(payment_status=ReservationPaymentStatus.PAID)
        assert ride.fully_reserved is False

    def test_pay_reservation_wrong_user(self, db):
        """Test cannot pay for another user's reservation"""
        passenger = UserFactory()
        other_user = UserFactory()
        reservation = ReservationFactory(passenger=passenger)

        with pytest.raises(
            ResourcePermissionError, match="You can only pay for your own reservations"
        ):
            ReservationService.pay_reservation(
                reservation_id=reservation.id, passenger=other_user
            )

    def test_pay_for_paid_ride_reservation(self, db, freezer):
        """Test cannot pay for a paid reservation"""
        passenger = UserFactory()

        # Create ride that departed 1 hour ago
        ride = RideFactory()
        reservation = ReservationFactory(
            ride=ride,
            passenger=passenger,
        )

        # Payment is done here
        ReservationService.pay_reservation(
            reservation_id=reservation.id, passenger=passenger
        )

        # Try paying again
        with pytest.raises(BusinessValidationError, match="already paid"):
            ReservationService.pay_reservation(
                reservation_id=reservation.id, passenger=passenger
            )

    def test_pay_for_a_reservation_ride_departed(self, db, freezer):
        """Test cannot pay for a reservation for departed ride"""
        passenger = UserFactory()
        now = timezone.now()
        freezer.move_to(now)

        # Create ride that departed 1 hour ago
        ride = RideFactory(departure_datetime=now - timedelta(hours=1))
        reservation = ReservationFactory(
            ride=ride,
            passenger=passenger,
        )

        with pytest.raises(BusinessValidationError, match="ride has started"):
            ReservationService.pay_reservation(
                reservation_id=reservation.id, passenger=passenger
            )

    def test_pay_reservation_not_found(self, db):
        """Test paying for non-existent reservation"""
        passenger = UserFactory()

        with pytest.raises(ObjectDoesNotExist, match="matching query does not exist"):
            ReservationService.pay_reservation(
                reservation_id="00000000-0000-0000-0000-000000000000",
                passenger=passenger,
            )

    # ----------------------------------------------------------------------
    # Get Reservation Stats Tests
    # ----------------------------------------------------------------------

    def test_get_reservation_stats_ride_owner(self, db):
        """Test ride owner can get reservation statistics"""
        driver = UserFactory()
        passenger1 = UserFactory()
        passenger2 = UserFactory()
        passenger3 = UserFactory()

        ride = RideFactory(user=driver, available_seats=5)

        # Create some reservations via service rather than factories
        ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=passenger1,
            seats_requested=2,
            price_per_seat=ride.price_per_seat,
        )

        ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=passenger2,
            seats_requested=1,
            price_per_seat=ride.price_per_seat,
        )

        # Create a reservation to be cancelled
        to_be_cancelled = ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=passenger3,
            seats_requested=1,
            price_per_seat=ride.price_per_seat,
        )

        # Trigger cancel via service
        ReservationService.cancel_reservation(
            reservation_id=to_be_cancelled.id, passenger=passenger3
        )

        # Refreshe the ride
        ride.refresh_from_db()

        stats = ReservationService.get_reservation_stats(ride.id, driver)

        assert stats["paid_reservations"] == 0
        assert stats["total_paid_seats"] == 0
        assert stats["pending_reservations"] == 2
        assert stats["total_unpaid_seats"] == 3  # 2 + 1 (excluding cancelled)

        assert stats["cancelled_count"] == 1
        assert (
            stats["available_seats"] == 2
        )  # The seats reamaining out of the initial 5
        assert stats["is_fully_reserved"] is False

    def test_get_reservation_stats_no_reservations(self, db):
        """Test stats when ride has no reservations"""
        driver = UserFactory()
        ride = RideFactory(user=driver, available_seats=4)

        stats = ReservationService.get_reservation_stats(ride.id, driver)

        assert stats["paid_reservations"] == 0
        assert stats["total_paid_seats"] == 0
        assert stats["pending_reservations"] == 0
        assert stats["total_unpaid_seats"] == 0
        assert stats["cancelled_count"] == 0
        assert stats["available_seats"] == 4
        assert stats["is_fully_reserved"] is False

    def test_get_reservation_stats_not_ride_owner(self, db):
        """Test non-owner cannot get stats"""
        driver = UserFactory()
        other_user = UserFactory()
        ride = RideFactory(user=driver)

        with pytest.raises(
            ResourcePermissionError,
            match="Only the ride owner can view reservation statistics",
        ):
            ReservationService.get_reservation_stats(ride.id, other_user)

    def test_get_reservation_stats_ride_not_found(self, db):
        """Test stats for non-existent ride"""
        user = UserFactory()

        with pytest.raises(ObjectDoesNotExist, match="matching query does not exist"):
            ReservationService.get_reservation_stats(
                ride_id="00000000-0000-0000-0000-000000000000", user=user
            )

    # ----------------------------------------------------------------------
    # Edge Cases and Validation Tests
    # ----------------------------------------------------------------------

    def test_create_multiple_reservations_same_passenger_different_rides(self, db):
        """Test passenger can create reservations for different rides"""
        passenger = UserFactory()
        ride1 = RideFactory(available_seats=3)
        ride2 = RideFactory(available_seats=3)

        reservation1 = ReservationService.create_reservation(
            ride_id=ride1.id,
            passenger=passenger,
            seats_requested=1,
            price_per_seat=ride1.price_per_seat,
        )

        reservation2 = ReservationService.create_reservation(
            ride_id=ride2.id,
            passenger=passenger,
            seats_requested=2,
            price_per_seat=ride2.price_per_seat,
        )

        assert reservation1.id is not None
        assert reservation2.id is not None
        assert reservation1.passenger == passenger
        assert reservation2.passenger == passenger

    def test_seat_consistency_with_multiple_reservations(self, db):
        """Test seat count remains consistent with multiple reservations"""
        driver = UserFactory()
        passenger1 = UserFactory()
        passenger2 = UserFactory()
        passenger3 = UserFactory()

        ride = RideFactory(user=driver, available_seats=5)

        # First reservation: 2 seats
        ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=passenger1,
            seats_requested=2,
            price_per_seat=ride.price_per_seat,
        )
        ride.refresh_from_db()
        assert ride.available_seats == 3

        # Second reservation: 2 seats
        ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=passenger2,
            seats_requested=2,
            price_per_seat=ride.price_per_seat,
        )
        ride.refresh_from_db()
        assert ride.available_seats == 1

        # Third reservation: 1 seat (filling the ride)
        ReservationService.create_reservation(
            ride_id=ride.id,
            passenger=passenger3,
            seats_requested=1,
            price_per_seat=ride.price_per_seat,
        )
        ride.refresh_from_db()
        assert ride.available_seats == 0
        assert ride.fully_reserved is True
