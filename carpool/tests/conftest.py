import pytest
from rest_framework.test import APIClient

from carpool.tests.factories import UserFactory


@pytest.fixture
def api_client():
    """Return an API client"""
    return APIClient()


@pytest.fixture
def authenticated_client():
    """Return an authenticated API client"""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


@pytest.fixture
def passenger_client():
    """Return an authenticated client for a passenger user"""
    passenger = UserFactory()
    client = APIClient()
    client.force_authenticate(user=passenger)
    client.user = passenger
    return client


@pytest.fixture
def another_client():
    """Return another authenticated client"""
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    client.user = user
    return client


@pytest.fixture
def user():
    """Return a regular user"""
    return UserFactory()


@pytest.fixture
def another_user():
    """Return another user"""
    return UserFactory()


@pytest.fixture
def ride(user):
    """Return a ride created by user"""
    from tests.factories import RideFactory

    return RideFactory(driver=user)


@pytest.fixture
def pending_request(ride, another_user):
    """Return a pending ride request"""
    from tests.factories import RideRequestFactory

    return RideRequestFactory(ride=ride, passenger=another_user)
