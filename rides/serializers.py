from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.serializers import SimpleUserSerializer
from rides.models import Ride

from ride_alerts.tasks import alert_users_for_ride

User = get_user_model()


class RideModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)
    class Meta:
        model= Ride
        fields= "__all__"
        
        read_only_fields = ["user", "is_active", "is_full"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        
        try:
            with transaction.atomic():
                new_ride = Ride.objects.create(**validated_data)
                # alert_users_for_ride.delay(new_ride.id)
                return new_ride
        except Exception as e:
            raise serializers.ValidationError(str(e))

