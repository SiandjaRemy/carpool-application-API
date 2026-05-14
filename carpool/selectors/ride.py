from typing import Optional, Dict, Any
from django.db.models import QuerySet
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.exceptions import NotFound

from carpool.enums.enums import RideStatus
from carpool.models import Ride
from carpool.filters import RideFilter

User = get_user_model()


class RideSelector:
    """
    Class-based selector for retrieving Ride data.
    Takes optional filter parameters and a user context.
    """

    def __init__(
        self, filters: Optional[Dict[str, Any]] = None, user: Optional[User] = None
    ):
        # Default to empty dict if no filters are provided
        self.filters = filters or {}
        self.user = user

    # --- 1. List Retrieval Methods ---

    def get_upcoming_rides(self) -> QuerySet[Ride]:
        """
        Returns upcoming, scheduled rides with available seats,
        filtered by the provided query parameters.
        """
        # 1. Get the base queryset using your custom manager methods
        base_qs = Ride.objects.upcoming()

        # 2. Apply django-filters
        # We pass the input data (self.filters) and the base queryset
        filterset = RideFilter(data=self.filters, queryset=base_qs)

        # 3. Return the filtered queryset (.qs extracts the QuerySet from the FilterSet)
        return filterset.qs

    def get_rides_for_user(self) -> QuerySet[Ride]:
        """
        Returns all rides created by the initialized user.
        """
        if not self.user:
            return Ride.objects.none()

        base_qs = Ride.objects.for_user(self.user)

        # Apply filters here as well, so the user can search their own rides!
        filterset = RideFilter(data=self.filters, queryset=base_qs)
        return filterset.qs

    # --- 2. Single Entity Retrieval Methods ---

    def get_ride_by_id(self, ride_id: str) -> Ride:
        """
        Retrieves a single ride. Uses get_object_or_404 to ensure
        the view logic remains clean.
        """
        return get_object_or_404(Ride, id=ride_id)

    def get_ride_detail_for_user(self, ride_id: str) -> Ride:
        """
        Specific retrieval that might include extra data
        optimization like prefetch_related for the detail view.
        """
        try:
            return (
                Ride.objects.select_related("user")
                .prefetch_related("reservations__user")  # Example: load passengers
                .get(id=ride_id)
            )
        except Ride.DoesNotExist:
            raise NotFound(detail="Ride not found.")

    # --- 3. Aggregate / Summary Methods ---

    def get_user_ride_stats(self) -> dict:
        """
        Example of a selector method that returns data structures
        rather than just QuerySets.
        """
        if not self.user:
            return {"total": 0, "completed": 0}

        user_rides = Ride.objects.filter(user=self.user)
        return {
            "total": user_rides.count(),
            "completed": user_rides.with_status(status=RideStatus.COMPLETED).count(),
        }
