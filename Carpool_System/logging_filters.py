import logging
from contextvars import ContextVar

# Thread-safe storage for current request
request_var: ContextVar = ContextVar("request_var", default=None)


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        """
        Enriches log records with request context:
        - request_id: Unique ID for tracking requests
        - user: Current authenticated user
        - ip: Client IP address
        """
        # Get the current request from thread-local storage
        request = request_var.get()

        if request:
            # Extract request ID (must be set elsewhere in middleware)
            record.request_id = getattr(request, "id", "")

            # Extract username or 'anonymous'
            record.user = getattr(
                getattr(request, "user", None), "username", "anonymous"
            )

            # Extract client IP address
            record.ip = request.META.get("REMOTE_ADDR", "")
        else:
            # Default values when no request context (e.g., Celery tasks)
            record.request_id = ""
            record.user = "anonymous"
            record.ip = ""

        return True  # Always allow the log through
