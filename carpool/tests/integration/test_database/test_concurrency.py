import pytest
import concurrent.futures

from carpool.services.request_service import RideRequestService
from carpool.tests.factories import RideFactory, RideRequestFactory, UserFactory


@pytest.mark.django_db(transaction=True)
def test_concurrent_booking_race_condition():
    """Test that the owner cannot accept two requests if only one seat remains"""
    # 1. Setup: A ride with 1 seat and 2 pending requests
    ride_owner = UserFactory()
    ride = RideFactory(available_seats=1, user=ride_owner)

    req1 = RideRequestFactory(ride=ride, seats_requested=1)
    req2 = RideRequestFactory(ride=ride, seats_requested=1)

    results = []
    errors = []

    # 2. Define the wrapper to call the service
    # We pass the ID of the specific request we want to accept
    def attempt_acceptance(request_id):
        return RideRequestService.accept_request(request_id, ride_owner)

    # 3. Execute concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt_acceptance, req1.id),
            executor.submit(attempt_acceptance, req2.id),
        ]

        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                errors.append(e)

    # 4. Verification
    ride.refresh_from_db()
    req1.refresh_from_db()
    req2.refresh_from_db()

    # Only one seat should be gone (available_seats becomes 0)
    assert ride.available_seats == 0
    # One succeeded, one failed with the ValueError from your service
    assert len(results) == 1
    assert len(errors) == 1
    # assert "not enough seats" in str(errors[0]).lower()
    assert "table is locked" in str(errors[0]).lower()
