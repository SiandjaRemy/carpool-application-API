from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from carpool.paginators import CustomPageNumberPagination

from carpool.models.reservation import Reservation
from carpool.serializers.reservation_serializers import ReservationsModelSerializer


class ReservationModelViewet(viewsets.ModelViewSet):
    http_method_names = ["get", "patch"]
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ReservationsModelSerializer

    def get_queryset(self):
        queryset = Reservation.objects.order_by("-created_at")

        return queryset

    def get_serializer_context(self):
        context = {}
        user = self.request.user
        if user.is_authenticated:
            context = {
                "user": user,
            }
        return context
