import pytest
import concurrent.futures
from django.db import IntegrityError, transaction

from carpool.models.ride import Ride
from carpool.tests.factories import RideFactory, UserFactory


# 1. Define the 'service' logic as a helper if it doesn't exist elsewhere
def create_booking_logic(ride_id, user):
    """
    Simulates the atomic logic inside your serializer/view
    """
    try:
        with transaction.atomic():
            # select_for_update() is the 'lock' that prevents the race condition
            ride = Ride.objects.select_for_update().get(id=ride_id)

            if ride.available_seats < 1:
                raise IntegrityError("No seats available")

            # Simulate a small delay to increase the chance of a collision
            # import time; time.sleep(0.1)

            ride.available_seats -= 1
            ride.save()
            return True
    except Exception as e:
        raise e


@pytest.mark.django_db(transaction=True)
def test_concurrent_booking_race_condition():
    """Test that two users can't book the last seat simultaneously"""
    ride = RideFactory(available_seats=1)
    user1 = UserFactory()
    user2 = UserFactory()

    # We use a wrapper to handle the executor calls
    def attempt_booking(user):
        return create_booking_logic(ride.id, user)

    # Simulate two concurrent requests
    # One should succeed, one should raise an error due to locking/validation
    results = []
    errors = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt_booking, user1),
            executor.submit(attempt_booking, user2),
        ]

        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                errors.append(e)

    # Verification
    ride.refresh_from_db()
    assert ride.available_seats == 0  # Only one seat should have been taken
    assert len(results) == 1  # One successful booking
    assert len(errors) == 1  # One failed booking
