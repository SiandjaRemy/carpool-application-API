from rest_framework import serializers

from django.contrib.auth import get_user_model

from accounts.serializers import SimpleUserSerializer
from carpool.models.request import RideRequest

User = get_user_model()


class RideRequestModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)

    class Meta:
        model = RideRequest
        fields = "__all__"

        read_only_fields = ["user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        return super().create(validated_data)
