from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.urls import NoReverseMatch

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework import status

import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    # Call DRF's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    if isinstance(exc, Throttled):
        wait_seconds = int(exc.wait)
        # Custom message with the exact wait time
        detail = f"Too many attempts. Please try again in {wait_seconds} seconds."
        return Response(
            {"detail": str(detail)}, status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    # If DRF didn't handle it, it's a custom Python exception or a server crash.
    if response is None:

        if isinstance(exc, NoReverseMatch):
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        elif isinstance(exc, ValueError):
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        elif isinstance(exc, ValidationError):
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # PermissionError becomes 403 Forbidden
        elif isinstance(exc, PermissionError):
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        # IntegrityError (database constraints) becomes 400 Bad Request
        elif isinstance(exc, IntegrityError):
            # Customize message for unique constraint violations
            if "UNIQUE constraint" in str(exc):
                return Response(
                    {"detail": "A duplicate entry already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"detail": f"Database integrity error: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ObjectDoesNotExist becomes 404 Not Found
        elif isinstance(exc, ObjectDoesNotExist):
            return Response(
                {"detail": "The requested resource was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # KeyError (missing context) becomes 400 Bad Request
        elif isinstance(exc, KeyError):
            return Response(
                {"detail": f"Missing required data: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Any other exception becomes 500 Internal Server Error
        else:
            # Log the full exception for debugging
            logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
            return Response(
                {"detail": "An unexpected server error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Optional: Ensure all DRF errors use the "detail" key and flatten lists
    if isinstance(response.data, dict):
        for key, value in response.data.items():
            if isinstance(value, list) and len(value) > 0:
                response.data[key] = value[0]

    return response
