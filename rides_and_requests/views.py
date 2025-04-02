from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from django.utils import timezone


from rides_and_requests.models import Ride, RideRequest, RideAlert
from rides_and_requests.serializers import (
    BlankSerializer,
    RideModelSerializer,
    RideRequestModelSerializer,
    RideAlertModelSerializer,
)
from rides_and_requests.paginators import CustomPageNumberPagination


class RideModelViewset(viewsets.ModelViewSet):
    serializer_class = RideModelSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        today = timezone.now()
        queryset = Ride.objects.filter(is_active=True, departure_datetime__gte=today)
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
            return RideModelSerializer
        elif self.request.method == "GET":
            return RideModelSerializer
        return BlankSerializer
    
    
    @action(methods=["GET"], detail=False, url_path="my-rides", permission_classes=[IsAuthenticated])
    def my_rides(self, request):
        user = self.request.user
        rides = (
            Ride.objects.select_related("user")
            .filter(user=user)
            .order_by("-created_at")
        )
        
        page = self.paginate_queryset(rides)
        
        if page is not None:
            return self.get_paginated_response(RideModelSerializer(page, many=True).data)
        
        my_rides = RideModelSerializer(rides, many=True)
        return Response(my_rides.data, status=status.HTTP_200_OK)
            
            
    @action(methods=["PATCH"], detail=True, url_path="toggle-active", permission_classes=[IsAuthenticated])
    def toggle_active(self, request, pk=None):
        if not pk:
            raise ValidationError({"error": "pk is required"})
        user = self.request.user
        try:
            ride = Ride.objects.filter(id=pk, user=user).first()
            ride.is_active = not ride.is_active
            ride.save()
        
        except Ride.DoesNotExist:
            raise ValidationError({"message": "No corresponding ride found"})
        except Exception as e:
            raise ValidationError({"error": str(e)})
            
            