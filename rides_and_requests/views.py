from rest_framework import viewsets

from rides_and_requests.serializers import (
    RideModelSerializer,
    RideRequestModelSerializer,
    RideAlertModelSerializer,
)


class RideModelViewset(viewsets.ModelViewSet):
    serializer_class = RideModelSerializer
    pagination_class = None