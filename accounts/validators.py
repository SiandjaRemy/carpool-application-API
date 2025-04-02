from rest_framework import serializers, status
from rest_framework.response import Response

from django.contrib.auth import get_user_model

User = get_user_model()


def validate_unique_email(lower_email):
    """Validator to check if the email corresponds to an existing users email"""
    # print(f"#################### {lower_email}")
    if User.objects.filter(email__iexact=lower_email).exists():
        raise serializers.ValidationError("User with corresponding email already exists")
    return lower_email



