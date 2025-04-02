from rest_framework import serializers

from django.contrib.auth import get_user_model

from rides_and_requests.models import Ride, RideAlert, RideRequest

User = get_user_model()


class RideModelSerializer(serializers.ModelSerializer):
    class Meta:
        model= Ride
        fields= "__all__"
        
        read_only_fields = ["user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        return super().create(validated_data)


class RideRequestModelSerializer(serializers.ModelSerializer):
    class Meta:
        model= RideRequest
        fields= "__all__"
        
        read_only_fields = ["user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        return super().create(validated_data)


class RideAlertModelSerializer(serializers.ModelSerializer):
    class Meta:
        model= RideAlert
        fields= "__all__"
        
        read_only_fields = ["user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        return super().create(validated_data)

