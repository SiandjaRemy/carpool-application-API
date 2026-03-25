class UUIDValidationMixin:
    """
    Reusable mixin to validate UUID URL parameters before processing.
    Can be configured per viewset for which URL parameters to validate.
    """

    lookup_value_regex = (
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )
