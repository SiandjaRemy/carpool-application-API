from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from django.db.models import Q

from carpool.caching import CacheMixin, cache_user_action
from carpool.mixins import UUIDValidationMixin
from carpool.paginators import CustomPageNumberPagination
from carpool.permissions import (
    IsRequestOwner,
    IsRequestOwnerOrReadOnly,
    IsRequestPending,
    IsRideOwner,
)

from carpool.models.request import RideRequest

from carpool.serializers.base_serializers import BlankSerializer
from carpool.serializers.request_serializers import (
    AcceptRideRequestSerializer,
    CancelRideRequestSerializer,
    RejectRideRequestSerializer,
    RideRequestModelSerializer,
)
from carpool.services.request_service import RideRequestService


class RideRequestModelViewset(CacheMixin, viewsets.ModelViewSet, UUIDValidationMixin):
    http_method_names = ["get", "post", "patch"]
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated, IsRequestOwnerOrReadOnly]

    cache_timeout = 300

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return RideRequest.objects.none()

        queryset = (
            RideRequest.objects.select_related("passenger")
            .filter(Q(ride__user=user) | Q(passenger=user))
            .filter(is_active=True)
            .order_by("-created_at")
        )
        return queryset

    def get_serializer_context(self):
        user = self.request.user
        context = {}
        if user.is_authenticated:
            ride_id = self.kwargs.get("rides_pk")
            request_id = self.kwargs.get("pk")
            context = {
                "user": user,
                "ride_id": ride_id,
                "request_id": request_id,
            }
        return context

    def get_serializer_class(self):
        """Return different serializers based on action"""
        if self.action == "toggle-active":
            return BlankSerializer
        elif self.action == "accept":
            return AcceptRideRequestSerializer
        elif self.action == "reject":
            return RejectRideRequestSerializer
        elif self.action == "cancel":
            return CancelRideRequestSerializer
        return RideRequestModelSerializer

    def get_exception_handler(self):
        return super().get_exception_handler()

    @cache_user_action(timeout=60 * 5)  # Caches custom action for 60 seconds
    @action(
        methods=["GET"],
        detail=False,
        url_path="my-request",
        url_name="my-request",
        permission_classes=[IsAuthenticated, IsRequestOwner],
    )
    def my_request(self, request, rides_pk=None):
        user = self.request.user
        ride_request = (  # Renamed variable to avoid shadowing 'request'
            RideRequest.objects.select_related("passenger")
            .filter(passenger=user, ride_id=rides_pk)
            .order_by("-created_at")
        ).first()

        # Check if object exists
        if not ride_request:
            return Response({}, status=status.HTTP_200_OK)

        serializer = RideRequestModelSerializer(ride_request, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="toggle-active",
        url_name="toggle-active",
        permission_classes=[IsAuthenticated, IsRequestOwner],
    )
    def toggle_active(self, request, rides_pk=None, pk=None):
        user = self.request.user
        updated_request = RideRequestService.toggle_request(request_id=pk, user=user)
        request_status = "Active" if updated_request.is_active else "Inactive"
        data = {"detail": f"Request is now {request_status}"}
        return Response(data, status=status.HTTP_200_OK)

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="accept",
        url_name="accept",
        permission_classes=[IsAuthenticated, IsRideOwner, IsRequestPending],
    )
    def accept_request(self, request, rides_pk=None, pk=None):
        """
        Accept a pending ride request and create a reservation.
        URL: /rides/{ride_id}/requests/{request_id}/accept/
        """
        serializer = AcceptRideRequestSerializer(
            data=request.data,
            context={
                "user": request.user,
                "ride_id": rides_pk,
                "request_id": pk,
            },
        )

        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": result["detail"],
                "request_status": result["request"].status,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="reject",
        url_name="reject",
        permission_classes=[IsAuthenticated, IsRideOwner, IsRequestPending],
    )
    def reject_request(self, request, rides_pk=None, pk=None):
        """
        Reject a pending ride request and create a reservation.
        URL: /rides/{ride_id}/requests/{request_id}/reject/
        """
        serializer = RejectRideRequestSerializer(
            data=request.data,
            context={
                "user": request.user,
                "ride_id": rides_pk,
                "request_id": pk,
            },
        )

        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": result["detail"],
                "request_status": result["request"].status,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="cancel",
        url_name="cancel",
        permission_classes=[IsAuthenticated, IsRequestOwner, IsRequestPending],
    )
    def cancel_request(self, request, rides_pk=None, pk=None):
        """
        Cancel a pending ride request and create a reservation.
        URL: /rides/{ride_id}/requests/{request_id}/cancel/
        """
        serializer = CancelRideRequestSerializer(
            data=request.data,
            context={
                "user": request.user,
                "ride_id": rides_pk,
                "request_id": pk,
            },
        )

        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": result["detail"],
                "request_status": result["request"].status,
            },
            status=status.HTTP_200_OK,
        )
