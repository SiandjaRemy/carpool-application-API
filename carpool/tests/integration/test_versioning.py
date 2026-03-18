import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestAPIVersioning:
    """Test that both API versions work"""

    def test_v1_rides_endpoint(self, api_client):
        """Test v1 rides endpoint is accessible"""
        url = reverse("v1:carpool:rides-list")
        response = api_client.get(url)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
        ]  # Depending on auth

    def test_v2_not_implemented_yet(self, api_client):
        """Test v2 returns 404 cause it's not implemented"""
        response = api_client.get("/api/v2/carpool/rides/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_version(self, api_client):
        """Test invalid version returns 404"""
        response = api_client.get("/api/v3/carpool/rides/")
        assert response.status_code == status.HTTP_404_NOT_FOUND
