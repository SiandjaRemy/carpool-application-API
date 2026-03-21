class ActionScopedThrottleMixin:
    """
    Mixin to dynamically set the throttle scope based on the action.
    Requires 'throttle_scope_mapping' to be defined in the ViewSet.
    """

    throttle_scope_mapping: dict = {}

    def get_throttles(self):
        # Check if the current action has a specific scope defined
        if self.action in self.throttle_scope_mapping:
            self.throttle_scope = self.throttle_scope_mapping[self.action]

        # You can also set a default scope for unmapped actions if you like
        # else:
        #     self.throttle_scope = "default_scope"

        return super().get_throttles()
