from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from django.utils import timezone


from ride_requests.models import RideRequest
from ride_requests.serializers import (
    RideRequestModelSerializer,
)

from utils.permissions import IsCreator, IsCreatorOrReadOnly
from utils.paginators import CustomPageNumberPagination
from utils.serializers import BlankSerializer


class RideRequestModelViewset(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]
    serializer_class = RideRequestModelSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly, IsCreatorOrReadOnly]

    def get_queryset(self):
        today = timezone.now()
        queryset = (
            RideRequest.objects.select_related("user")
            .filter(is_active=True, departure_datetime__gte=today)
            .order_by("-created_at")
        )
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
            return RideRequestModelSerializer
        elif self.request.method == "GET":
            return RideRequestModelSerializer
        return BlankSerializer

    @action(
        methods=["GET"],
        detail=False,
        url_path="my-requests",
        permission_classes=[IsAuthenticated],
    )
    def my_requests(self, request):
        user = self.request.user
        requests = (
            RideRequest.objects.select_related("user")
            .filter(user=user)
            .order_by("-created_at")
        )

        page = self.paginate_queryset(requests)

        if page is not None:
            return self.get_paginated_response(
                RideRequestModelSerializer(page, many=True).data
            )

        my_requests = RideRequestModelSerializer(requests, many=True)
        return Response(my_requests.data, status=status.HTTP_200_OK)

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
            request = RideRequest.objects.get(id=pk, user=user)
            request.is_active = not request.is_active
            request.save()
            request_status = "Active" if request.is_active else "Inactive"
            data = {"message": f"Request is now {request_status}"}
            return Response(data, status=status.HTTP_200_OK)

        except RideRequest.DoesNotExist:
            raise ValidationError({"message": "No corresponding request found"})
        except Exception as e:
            raise ValidationError({"error": str(e)})
