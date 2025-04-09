from rest_framework import serializers

from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.serializers import SimpleUserSerializer
from ride_requests.models import RideRequest

User = get_user_model()



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

