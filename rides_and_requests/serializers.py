from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.serializers import SimpleUserSerializer
from rides_and_requests.models import Ride, RideAlert, RideRequest
from rides_and_requests.tasks import alert_users_for_ride

User = get_user_model()


class RideModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)
    class Meta:
        model= Ride
        fields= "__all__"
        
        read_only_fields = ["user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        
        try:
            with transaction.atomic():
                new_ride = Ride.objects.create(**validated_data)
                alert_users_for_ride.delay(new_ride.id)
                return new_ride
        except Exception as e:
            raise serializers.ValidationError(str(e))


class RideRequestModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)
    class Meta:
        model= RideRequest
        fields= "__all__"
        
        read_only_fields = ["user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        return super().create(validated_data)


class RideAlertModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)
    class Meta:
        model= RideAlert
        fields= "__all__"
        
        read_only_fields = ["user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        return super().create(validated_data)



class BlankSerializer(serializers.Serializer):
    pass