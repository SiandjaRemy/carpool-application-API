from rest_framework import viewsets
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import MethodNotAllowed

from carpool.paginators import CustomPageNumberPagination

from carpool.models.reservation import Reservation
from carpool.permissions import IsRequestOwner
from carpool.serializers.reservation_serializers import (
    CancelReservationSerializer,
    ReservationsModelSerializer,
)


class ReservationModelViewet(viewsets.ModelViewSet):
    http_method_names = ["get", "patch"]
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated]

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
        if self.action == "cancel":
            return CancelReservationSerializer
        return ReservationsModelSerializer

    def partial_update(self, request, *args, **kwargs):
        """Prevent PATCH updates (unless it's our custom cancel action)"""
        # Allow PATCH only for our custom cancel action
        if self.action == "cancel":
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

        try:
            result = serializer.save()

            return Response(
                {
                    "detail": result["detail"],
                    "reservation_status": result["reservation"].status,
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            # Handle validation errors (400)
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            # Handle permission errors (403)
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            # Handle unexpected errors (500)
            return Response(
                {"detail": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
