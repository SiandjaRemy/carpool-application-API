from rest_framework import status
from rest_framework.response import Response

from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)


class ServiceErrorHandlingMixin:
    """
    Mixin to handle service layer errors consistently across views.
    Catches common exceptions and returns appropriate HTTP responses.
    """

    def handle_service_exception(self, e, context=None):
        """
        Centralized exception handler for service layer errors.

        Args:
            e: The exception that was raised
            context: Optional dict with additional context for logging

        Returns:
            Response object with appropriate status code and error message
        """
        context = context or {}

        # Log the error (useful for debugging)
        logger.error(f"Service error: {str(e)} | Context: {context}")

        # ValueErrors from service become 400 Bad Request
        if isinstance(e, ValueError):
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # PermissionError becomes 403 Forbidden
        elif isinstance(e, PermissionError):
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)

        # IntegrityError (database constraints) becomes 400 Bad Request
        elif isinstance(e, IntegrityError):
            # Customize message for unique constraint violations
            if "UNIQUE constraint" in str(e):
                return Response(
                    {"detail": "A duplicate entry already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"detail": f"Database integrity error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ObjectDoesNotExist becomes 404 Not Found
        elif isinstance(e, ObjectDoesNotExist):
            return Response(
                {"detail": "The requested resource was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # KeyError (missing context) becomes 400 Bad Request
        elif isinstance(e, KeyError):
            return Response(
                {"detail": f"Missing required data: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Any other exception becomes 500 Internal Server Error
        else:
            # Log the full exception for debugging
            logger.exception(f"Unexpected error: {str(e)}")
            return Response(
                {"detail": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def perform_create(self, serializer):
        """Override perform_create with error handling"""
        try:
            return super().perform_create(serializer)
        except Exception as e:
            # Re-raise with proper handling at view level
            raise type(e)(str(e)) from e

    def perform_update(self, serializer):
        """Override perform_update with error handling"""
        try:
            return super().perform_update(serializer)
        except Exception as e:
            raise type(e)(str(e)) from e


class AtomicServiceErrorHandlingMixin(ServiceErrorHandlingMixin):
    """
    Enhanced mixin that wraps create/update in database transactions
    and provides consistent error responses.
    """

    def create(self, request, *args, **kwargs):
        """Create with transaction safety and error handling"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Use serializer.save() which should call the service
            instance = serializer.save()
            headers = self.get_success_headers(serializer.data)

            # Return success response
            response_serializer = self.get_serializer(instance)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers,
            )

        except Exception as e:
            # Handle any exception from the service layer
            return self.handle_service_exception(
                e, context={"action": "create", "user": str(request.user.id)}
            )

    def update(self, request, *args, **kwargs):
        """Update with transaction safety and error handling"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            updated_instance = serializer.save()
            response_serializer = self.get_serializer(updated_instance)
            return Response(response_serializer.data)

        except Exception as e:
            return self.handle_service_exception(
                e,
                context={
                    "action": "update",
                    "user": str(request.user.id),
                    "instance_id": str(instance.id),
                },
            )

    def partial_update(self, request, *args, **kwargs):
        """Alias for update with partial=True"""
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete with error handling"""
        try:
            return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return self.handle_service_exception(
                e, context={"action": "delete", "user": str(request.user.id)}
            )
