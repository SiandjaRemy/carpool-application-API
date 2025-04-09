from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.serializers import SimpleUserSerializer
from passengers.models import Passenger

User = get_user_model()


class PassengerModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)
    ride_id = serializers.UUIDField()
    
    class Meta:
        model= Passenger
        fields= "__all__"
        
        read_only_fields = ["user", "ride"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        
        # ride_id = validated_data["ride_id"]
        
        try:
            with transaction.atomic():
                passenger = Passenger.objects.create(**validated_data)
                return passenger
        except Exception as e:
            raise serializers.ValidationError(str(e))

