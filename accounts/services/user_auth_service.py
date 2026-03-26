from django.contrib.auth import get_user_model
from django.db import transaction


from accounts.validators import validate_unique_email

User = get_user_model()


class UserAuthService:

    @staticmethod
    def _validate_user_creation(user_data):
        """Validate user data before creation"""
        # Ensure that account with similar email does not exists
        lower_email = user_data["email"]
        validate_unique_email(lower_email)
        # Unique username can also be checked

    @classmethod
    @transaction.atomic
    def create_user(cls, user_data):
        """
        Create a new user with unique email validation
        """

        # set to lowercase
        user_data["email"] = user_data["email"].lower()
        user_data["username"] = user_data["username"].lower()
        user_data["first_name"] = user_data["first_name"].lower()
        user_data["last_name"] = user_data["last_name"].lower()

        # Validate
        cls._validate_user_creation(user_data)

        try:
            # Create the user
            user = User.objects.create(**user_data)
            return user
        except Exception as e:
            raise ValueError(f"Failed to create user: {str(e)}")

    @classmethod
    @transaction.atomic
    def update_user(cls, update_data, instance, user):
        """
        Update an existing ride
        """
        if instance.id != user.id:
            raise ValueError("User not found or you don't have permission")

        # Validate update
        cls._validate_user_update(instance, update_data)

        # Update fields
        for field, value in update_data.items():
            setattr(instance, field, value)

        instance.save(update_fields=list(update_data.keys()))

        return instance
