from rest_framework.throttling import ScopedRateThrottle


class ActionScopedThrottleMixin:
    """
    Mixin to dynamically set the throttle scope based on the action.
    Requires 'throttle_scope_mapping' to be defined in the ViewSet.
    """

    throttle_scope_mapping: dict = {}

    # Optional: Define a fallback scope for actions not in the mapping
    default_throttle_scope: str = None

    def get_throttles(self):
        # 1. Safely get the action (protects against schema generation edge cases)
        action = getattr(self, "action", None)

        # 2. Set the scope based on mapping, or fallback to the default
        if action and action in self.throttle_scope_mapping:
            self.throttle_scope = self.throttle_scope_mapping[action]
        elif self.default_throttle_scope:
            self.throttle_scope = self.default_throttle_scope
        else:
            self.throttle_scope = "default_scope"

        # 3. Validation: Ensure ScopedRateThrottle is actually being used
        throttles = super().get_throttles()
        has_scoped_throttle = any(isinstance(t, ScopedRateThrottle) for t in throttles)

        if getattr(self, "throttle_scope", None) and not has_scoped_throttle:
            import logging

            logging.getLogger(__name__).warning(
                f"ViewSet {self.__class__.__name__} has a throttle_scope set, "
                "but ScopedRateThrottle is missing from throttle_classes."
            )

        return throttles
