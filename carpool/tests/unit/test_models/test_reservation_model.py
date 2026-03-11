import pytest

from django.core.exceptions import ValidationError

from carpool.models import Reservation
from carpool.enums.enums import ReservationPaymentStatus

from tests.factories import (
    ReservationFactory,
    ConfirmedReservationFactory,
    RideFactory,
    RideRequestFactory,
    UserFactory,
)

pytestmark = pytest.mark.unit


class TestReservationModel:

    def test_create_reservation(self, db):
        """Test creating a reservation with valid data"""
        ride = RideFactory()
        passenger = UserFactory()

        reservation = Reservation.objects.create(
            ride=ride, passenger=passenger, seats_requested=2, price_per_seat=25.50
        )

        assert reservation.id is not None
        assert reservation.payment_status == ReservationPaymentStatus.PENDING
        assert reservation.confirmed_at is None
        assert not reservation.is_confirmed

    def test_reservation_factory_creates_valid_reservation(self, db):
        """Test reservation factory creates valid objects"""
        reservation = ReservationFactory()

        assert reservation.id is not None
        assert reservation.payment_status == ReservationPaymentStatus.PENDING
        assert reservation.seats_requested >= 1
        assert reservation.seats_requested <= 10
        assert reservation.price_per_seat == 25.50

    def test_reservation_factory_creates_valid_reservation_from_a_ride_request(
        self, db
    ):
        """Test reservation factory creates valid objects"""
        ride_request = RideRequestFactory()
        reservation = ReservationFactory.from_request(ride_request)

        assert reservation.id is not None
        assert reservation.payment_status == ReservationPaymentStatus.PENDING
        assert reservation.seats_requested == ride_request.seats_requested
        assert reservation.price_per_seat == ride_request.price_per_seat

    def test_is_confirmed_property(self, db):
        """Test is_confirmed property returns correct value"""
        pending_reservation = ReservationFactory(confirmed_at=None)
        assert not pending_reservation.is_confirmed

        confirmed_reservation = ConfirmedReservationFactory()
        assert confirmed_reservation.is_confirmed

    def test_seats_requested_validation(self, db):
        """Test seats_requested field validation"""
        ride = RideFactory()
        passenger = UserFactory()

        # Test minimum seats
        with pytest.raises(ValidationError):
            reservation = Reservation(
                ride=ride,
                passenger=passenger,
                seats_requested=0,  # Invalid
                price_per_seat=25.50,
            )
            reservation.full_clean()

        # Test maximum seats
        with pytest.raises(ValidationError):
            reservation = Reservation(
                ride=ride,
                passenger=passenger,
                seats_requested=11,  # Invalid
                price_per_seat=25.50,
            )
            reservation.full_clean()

    def test_price_per_seat_positive(self, db):
        """Test price_per_seat must be positive"""
        ride = RideFactory()
        passenger = UserFactory()

        with pytest.raises(ValidationError):
            reservation = Reservation(
                ride=ride,
                passenger=passenger,
                seats_requested=2,
                price_per_seat=-10.0,  # Invalid
            )
            reservation.full_clean()
