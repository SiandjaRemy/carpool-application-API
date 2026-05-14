from typing import TYPE_CHECKING, Literal

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from carpool.enums.enums import RideStatus

User = get_user_model()

# Using TYPE_CHECKING prevents circular imports at runtime.
if TYPE_CHECKING:
    from carpool.models.ride import Ride


class RideQuerySet(models.QuerySet["Ride"]):

    def for_route(self, *, departure_town: str, arrival_town: str) -> "RideQuerySet":
        return self.filter(
            departure_town__iexact=departure_town,
            arrival_town__iexact=arrival_town,
        )

    def available(self) -> "RideQuerySet":
        queryset = self.filter(
            available_seats__gt=0,
        )
        return queryset

    def future(self) -> "RideQuerySet":
        current_time = timezone.now()
        queryset = self.filter(
            departure_datetime__gte=current_time,
        )
        return queryset

    def with_status(
        self,
        *,
        status: Literal[
            RideStatus.SCHEDULED,
            RideStatus.IN_PROGRESS,
            RideStatus.COMPLETED,
            RideStatus.CANCELLED,
        ],
    ):
        queryset = self.filter(
            status=status,
        )
        return queryset

    def upcoming(self) -> "RideQuerySet":
        queryset = (
            self.select_related("user")
            .available()
            .future()
            .with_status(RideStatus.SCHEDULED)
            .order_by("-created_at")
        )
        return queryset

    def for_user(self, *, user: User) -> "RideQuerySet":
        queryset = self.filter(user=user).order_by("-created_at")
        return queryset


class RideManager(models.Manager["Ride"]):

    def get_queryset(self) -> RideQuerySet:
        return RideQuerySet(self.model, using=self._db)

    def future(self) -> RideQuerySet:
        return self.get_queryset().future()

    def for_route(self, *, departure_town: str, arrival_town: str) -> RideQuerySet:
        return self.get_queryset().for_route(
            departure_town=departure_town, arrival_town=arrival_town
        )

    def available(self) -> RideQuerySet:
        return self.get_queryset().available()

    def with_status(
        self,
        *,
        status: Literal[
            RideStatus.SCHEDULED,
            RideStatus.IN_PROGRESS,
            RideStatus.COMPLETED,
            RideStatus.CANCELLED,
        ],
    ):
        return self.get_queryset().with_status(status=status)

    def upcoming(self) -> RideQuerySet:
        return self.get_queryset().upcoming()

    def for_user(self, *, user: User) -> RideQuerySet:
        return self.get_queryset().for_user(user=user)
