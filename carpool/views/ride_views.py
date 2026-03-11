from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from django.utils import timezone

from carpool.enums.enums import RideStatus
from carpool.paginators import CustomPageNumberPagination
from carpool.permissions import IsCreator, IsCreatorOrReadOnly

from carpool.models.ride import Ride

from carpool.serializers.base_serializers import BlankSerializer
from carpool.serializers.ride_serializers import (
    RideModelSerializer,
    RideUpdateSerializer,
)


class RideModelViewset(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch"]
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]

    def get_queryset(self):
        current_time = timezone.now()
        queryset = (
            Ride.objects.select_related("user")
            .filter(
                status=RideStatus.SHECDULED,
                departure_datetime__gte=current_time,
                available_seats__gt=0,
            )
            .order_by("-created_at")
        )
        return queryset

    def get_serializer_context(self):
        """Add user to serializer context for create operations"""
        user = self.request.user
        context = {}
        if user.is_authenticated:
            context = {
                "user": user,
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
        url_path="toggle-active",
        permission_classes=[IsAuthenticated, IsCreator],
    )
    def toggle_active(self, request, pk=None):
        if not pk:
            raise ValidationError({"error": "pk is required"})
        user = self.request.user
        try:
            ride = Ride.objects.get(id=pk, user=user)
            ride.is_active = not ride.is_active
            ride.save()
            ride_status = "Active" if ride.is_active else "Inactive"
            data = {"message": f"Ride is now {ride_status}"}
            return Response(data, status=status.HTTP_200_OK)

        except Ride.DoesNotExist:
            raise ValidationError({"message": "No corresponding ride found"})
        except Exception as e:
            raise ValidationError({"error": str(e)})
