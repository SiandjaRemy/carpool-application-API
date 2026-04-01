class ServiceException(Exception):
    """Base class for all service-related errors."""

    def __init__(self, message, details=None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class BusinessValidationError(ServiceException):
    """Raise when business rules are violated (HTTP 400)."""

    pass


class ResourcePermissionError(ServiceException):
    """Raise when a user tries to access something they don't own (HTTP 403)."""

    pass


class ResourceNotFoundError(ServiceException):
    """Raise when an object isn't found (HTTP 404)."""

    pass
