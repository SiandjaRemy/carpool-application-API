from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from djoser.serializers import UserSerializer
from django.utils import timezone
from accounts.models import User

from accounts.validators import validate_unique_email


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token["is_superuser"] = user.is_superuser
        token["user_id"] = str(user.id)

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        if not user.is_active:
            raise ValidationError(
                {"message": "This account is inactive. Please contact support."}
            )

        return data


class UserCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True
    )  # Don't allow email to be set during creation (more secure)
    username = serializers.CharField(max_length=50)  # Convert to lowercase befor savng
    first_name = serializers.CharField(max_length=50, required=False)
    last_name = serializers.CharField(max_length=50, required=False)
    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )  # Add password field
    status = serializers.UUIDField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
            "status",
        ]
        read_only_fields = ["id", "status"]
        
    def validate_email(self, value):
        """Convert email to lowercase and check for uniqueness."""
        lower_email = value.lower()
        # Check if email exists case-insensitive
        return validate_unique_email(lower_email)
        

    def create(self, validated_data):  # Override create, not save
        """Creates and returns a new User instance, given the validated data."""
        # Convert to lower case
        validated_data["email"] = validated_data["email"].lower()
        validated_data["username"] = validated_data["username"].lower()
        validated_data["first_name"] = validated_data["first_name"].lower()
        validated_data["last_name"] = validated_data["last_name"].lower()

        user = User.objects.create_user(
            **validated_data
        )  # Create user using create_user

        return user

    def update(self, instance, validated_data):
        raise NotImplementedError("Update is not supported for user creation.")



class UserDataSerializer(UserSerializer):
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(max_length=50, required=False)
    last_name = serializers.CharField(max_length=50, required=False)
    is_active = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_superuser",
        ]


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name"]


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        style={"input_type": "password"}, required=True
    )
    new_password = serializers.CharField(
        style={"input_type": "password"}, required=True
    )

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise ValidationError({"current_password": "Does not match"})
        return value


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    uid = serializers.CharField(required=True)
    new_password = serializers.CharField(
        style={"input_type": "password"}, required=True
    )
    re_new_password = serializers.CharField(
        style={"input_type": "password"}, required=True
    )

    def validate(self, data):
        if data["new_password"] != data["re_new_password"]:
            raise ValidationError("Passwords do not match.")
        return data


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)
