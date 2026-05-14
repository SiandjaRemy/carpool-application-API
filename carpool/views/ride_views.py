from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.throttling import ScopedRateThrottle

from django.utils import timezone

from Carpool_System.core.paginators import CustomPageNumberPagination
from Carpool_System.core.caching import CacheMixin
from Carpool_System.core.mixins import UUIDValidationMixin
from Carpool_System.core.throttling import ActionScopedThrottleMixin

from carpool.permissions import IsCreatorOrReadOnly, IsRideOwner

from carpool.models.ride import Ride

from carpool.serializers.base_serializers import BlankSerializer
from carpool.serializers.ride_serializers import (
    CancelRideSerializer,
    RideModelSerializer,
    RideUpdateSerializer,
)


class RideModelViewset(
    ActionScopedThrottleMixin, CacheMixin, viewsets.ModelViewSet, UUIDValidationMixin
):
    http_method_names = ["get", "post", "patch"]
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]

    cache_timeout = 300

    throttle_classes = [ScopedRateThrottle]

    throttle_scope_mapping = {
        "list": "list",
        "retrieve": "retrieve",
        "create": "user_create",
        "partial_update": "user_update",
        "my_rides": "list",
        "cancel_ride": "user_custom",
    }

    def get_queryset(self):
        queryset = Ride.objects.upcoming()
        return queryset

    def get_serializer_context(self):
        """Add user to serializer context for create operations"""
        user = self.request.user
        context = {}
        ride_id = self.kwargs.get("pk")
        if user.is_authenticated:
            context = {
                "user": user,
                "ride_id": ride_id,
            }
        return context

    def get_serializer_class(self):
        """Return different serializers based on action"""
        if self.action in ["update", "partial_update"]:
            return RideUpdateSerializer
        elif self.action in ["create", "retrieve", "list"]:
            return RideModelSerializer
        return BlankSerializer

    @action(
        methods=["GET"],
        detail=False,
        url_path="my-rides",
        permission_classes=[IsAuthenticated],
    )
    def my_rides(self, request):
        user = self.request.user
        rides = (
            Ride.objects.select_related("user")
            .filter(user=user)
            .order_by("-created_at")
        )

        page = self.paginate_queryset(rides)

        if page is not None:
            return self.get_paginated_response(
                RideModelSerializer(page, many=True).data
            )

        my_rides = RideModelSerializer(rides, many=True)
        return Response(my_rides.data, status=status.HTTP_200_OK)

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="cancel",
        url_name="cancel",
        permission_classes=[IsAuthenticated, IsRideOwner],
    )
    def cancel_ride(self, request, pk=None):
        """
        Cancel a ride and refund passengers if needed.
        """
        serializer = CancelRideSerializer(
            data=request.data,
            context={
                "user": request.user,
                "ride_id": pk,
            },
        )

        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": result["detail"],
                "ride_status": result["ride"].status,
            },
            status=status.HTTP_200_OK,
        )
