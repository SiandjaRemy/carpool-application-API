from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError


from passengers.models import Passenger
from passengers.serializers import (
    PassengerModelSerializer,
    RegisterPassengerModelSerializer,
)

from rides.models import Ride
from utils.paginators import CustomPageNumberPagination


class RegisterPassengerForRideGenericView(generics.CreateAPIView):
    serializer_class = RegisterPassengerModelSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Passenger.objects.select_related("user").filter(ride__is_active=True).order_by(
            "-created_at"
        )
        return queryset

    def get_serializer_context(self):
        user = self.request.user
        context = {
            "user": user,
        }
        return context

    """Allow users to buy seats in for a ride"""

    def post(self, request):
        data = self.request.data

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            
            # passenger = serializer.save()
            # serialized_data = PassengerModelSerializer(passenger, many=False)
            # return Response(serialized_data.data, status=status.HTTP_200_OK)

            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetPassengersForRideGenericView(generics.ListAPIView):
    serializer_class = PassengerModelSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        ride_pk = self.kwargs.get("ride_pk")
        queryset = (
            Passenger.objects.select_related("ride", "user")
            .filter(ride_id=ride_pk)
            .order_by("-created_at")
        )
        # Think about annotating the count and reusing it below
        return queryset
    
    def get_serializer_context(self):
        user = self.request.user
        ride_pk = self.kwargs.get("ride_pk")
        context = {}
        if user.is_authenticated:
            context = {
                "user": user,
                "ride_pk": ride_pk,
            }
        return context

    def get(self, request, ride_pk=None):
        if not ride_pk:
            raise ValidationError({"message": "transaction id required"})

        ride_passengers = self.get_queryset()

        transaction_exists = Ride.objects.filter(id=ride_pk).exists()
        if not transaction_exists:
            raise ValidationError({"message": "Corresponding ride does not exist"})

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(ride_passengers, request=request)

        if page is not None:
            serializer = PassengerModelSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = PassengerModelSerializer(ride_passengers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
