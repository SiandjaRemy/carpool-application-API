from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from core.paginators import CustomPageNumberPagination

from reservations.models import Reservation
from reservations.serializers import ReservationsModelSerializer


class ReservationgModelViewet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch"]
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
