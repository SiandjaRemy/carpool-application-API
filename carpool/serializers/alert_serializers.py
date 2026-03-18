from rest_framework import serializers

from django.contrib.auth import get_user_model

from accounts.serializers import SimpleUserSerializer
from carpool.models.alert import RideAlert
from carpool.services.alert_service import RideAlertService

User = get_user_model()


class RideAlertModelSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(many=False, read_only=True)
    after_date = serializers.DateTimeField(required=True)
    before_date = serializers.DateTimeField(required=True)

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

        read_only_fields = ["id", "user", "is_active"]

    def create(self, validated_data):
        user = self.context["user"]

        ride_alert = RideAlertService.create_alert(user=user, alert_data=validated_data)

        return ride_alert


class RideAlertUpdateModelSerializer(serializers.ModelSerializer):
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
        read_only_fields = ["id", "user", "is_active"]

    def update(self, instance, validated_data):
        user = self.context["user"]

        updated_alert = RideAlertService.update_alert(
            update_data=validated_data,
            instance=instance,
            user=user,
        )

        return updated_alert
