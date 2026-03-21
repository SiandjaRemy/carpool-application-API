from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from carpool.caching import CacheMixin
from carpool.mixins import UUIDValidationMixin
from carpool.paginators import CustomPageNumberPagination
from carpool.permissions import IsAlertOwner

from carpool.models.alert import RideAlert

from carpool.serializers.alert_serializers import (
    RideAlertModelSerializer,
    RideAlertUpdateModelSerializer,
)
from carpool.serializers.base_serializers import BlankSerializer


from carpool.services.alert_service import RideAlertService


class RideAlertModelViewset(CacheMixin, viewsets.ModelViewSet, UUIDValidationMixin):
    http_method_names = ["get", "post", "patch"]
    serializer_class = RideAlertModelSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated, IsAlertOwner]

    cache_timeout = 300

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            queryset = (
                RideAlert.objects.select_related("user")
                .filter(user=user)
                .order_by("-created_at")
            )
        else:
            queryset = RideAlert.objects.none()
        return queryset

    def get_serializer_context(self):
        user = self.request.user
        context = {}
        if user.is_authenticated:
            context = {
                "user": user,
            }
        return context

    def get_serializer_class(self):
        if self.action == "toggle-active":
            return BlankSerializer
        elif self.action == "partial_update":
            return RideAlertUpdateModelSerializer
        return RideAlertModelSerializer

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="toggle-active",
        permission_classes=[IsAuthenticated, IsAlertOwner],
    )
    def toggle_active(self, request, pk=None):
        user = self.request.user
        alert = RideAlertService.toggle_alert(alert_id=pk, user=user)
        alert_status = "Active" if alert.is_active else "Inactive"
        data = {"message": f"Alert is now {alert_status}"}
        return Response(data, status=status.HTTP_200_OK)
