from rest_framework import viewsets
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import MethodNotAllowed

from Carpool_System.core.caching import CacheMixin
from Carpool_System.core.mixins import UUIDValidationMixin
from Carpool_System.core.paginators import CustomPageNumberPagination

from carpool.models.reservation import Reservation
from carpool.permissions import IsRequestOwner
from carpool.serializers.reservation_serializers import (
    CancelReservationSerializer,
    PayReservationSerializer,
    ReservationsModelSerializer,
)


class ReservationModelViewset(CacheMixin, viewsets.ModelViewSet, UUIDValidationMixin):
    http_method_names = ["get", "patch"]
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated]

    cache_timeout = 300

    def get_queryset(self):
        user = self.request.user

        if not user.is_authenticated:
            return Reservation.objects.none()

        # Regular users see only their own reservations
        # Ride owners might see reservations for their rides (if you want that)
        return (
            Reservation.objects.filter(passenger=user)
            .select_related("ride", "passenger")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        user = self.request.user
        context = {}
        if user.is_authenticated:
            reservation_id = self.kwargs.get("pk")
            context = {
                "user": user,
                "reservation_id": reservation_id,
            }
        return context

    def get_serializer_class(self):
        """Return different serializers based on action"""
        if self.action == "payment":
            return PayReservationSerializer
        return ReservationsModelSerializer

    def partial_update(self, request, *args, **kwargs):
        """Prevent PATCH updates (unless it's our custom actions)"""
        # Allow PATCH only for our custom cancel action
        if self.action in ["cancel", "payment"]:
            return super().partial_update(request, *args, **kwargs)

        raise MethodNotAllowed(
            method="PATCH",
            detail="Direct updates are not allowed. Use an action instead.",
        )

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="cancel",
        url_name="cancel",
        permission_classes=[IsAuthenticated, IsRequestOwner],
    )
    def cancel_reservation(self, request, pk=None):
        """
        Cancel a reservation and get refunded if necessary.
        """
        serializer = CancelReservationSerializer(
            data=request.data,
            context={
                "user": request.user,
                "reservation_id": pk,
            },
        )

        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": result["detail"],
                "reservation_status": result["reservation"].status,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="payment",
        url_name="payment",
        permission_classes=[IsAuthenticated, IsRequestOwner],
    )
    def pay_reservation(self, request, pk=None):
        """
        Trigger payment for a conversation.
        """
        serializer = PayReservationSerializer(
            data=request.data,
            context={
                "user": request.user,
                "reservation_id": pk,
            },
        )

        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "detail": result["detail"],
                "reservation_status": result["reservation"].status,
            },
            status=status.HTTP_200_OK,
        )
