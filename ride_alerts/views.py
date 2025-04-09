from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from django.utils import timezone


from ride_alerts.models import RideAlert
from ride_alerts.serializers import (
    RideAlertModelSerializer,
)

from utils.permissions import IsCreator, IsCreatorOrReadOnly
from utils.paginators import CustomPageNumberPagination
from utils.serializers import BlankSerializer


class RideAlertModelViewset(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = RideAlertModelSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated, IsCreator]

    def get_queryset(self):
        today = timezone.now()
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
        if self.request.method == "POST":
            return RideAlertModelSerializer
        elif self.request.method == "GET":
            return RideAlertModelSerializer
        return BlankSerializer

    @action(
        methods=["PATCH"],
        detail=True,
        url_path="toggle-active",
        permission_classes=[IsAuthenticated],
    )
    def toggle_active(self, request, pk=None):
        if not pk:
            raise ValidationError({"error": "pk is required"})
        user = self.request.user
        try:
            request = RideAlert.objects.get(id=pk, user=user)
            request.is_active = not request.is_active
            request.save()
            request_status = "Active" if request.is_active else "Inactive"
            data = {"message": f"Alert is now {request_status}"}
            return Response(data, status=status.HTTP_200_OK)

        except RideAlert.DoesNotExist:
            raise ValidationError({"message": "No corresponding alert found"})
        except Exception as e:
            raise ValidationError({"error": str(e)})
