from rest_framework import serializers

from django.contrib.auth import get_user_model

from accounts.serializers import SimpleUserSerializer
from carpool.models.alert import RideAlert

User = get_user_model()


class RideAlertModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)

    class Meta:
        model = RideAlert
        fields = [
            "id",
            "user",
            "departure_town",
            "arrival_town",
            "before_date",
            "after_date",
            "is_active",
        ]

        read_only_fields = ["user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        return super().create(validated_data)
