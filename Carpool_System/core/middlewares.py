import math
from django.utils.deprecation import MiddlewareMixin


class RateLimitHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add X-RateLimit-Limit, X-RateLimit-Remaining,
    and X-RateLimit-Reset headers to DRF responses.
    """

    def process_response(self, request, response):
        # DRF attaches 'throttle_scope' to the request if ScopedRateThrottle was used
        view = getattr(request, "resolver_match", None)
        if not view:
            return response

        # Try to find the throttle instances applied to this request
        # This requires the view to have been processed by DRF's dispatch
        try:
            # We only proceed if this was a DRF View
            view_instance = view.func.view_class()
            throttles = view_instance.get_throttles()
        except AttributeError:
            return response

        for throttle in throttles:
            # We only care about throttles that have a 'rate' (like ScopedRateThrottle)
            if hasattr(throttle, "num_requests") and hasattr(throttle, "duration"):
                limit = throttle.num_requests
                # Get the history of requests from cache
                history = throttle.get_history(request)
                remaining = max(0, limit - len(history))

                # Calculate reset time (when the oldest request in history expires)
                if history:
                    reset = math.ceil(history[-1] - history[0] + throttle.duration)
                else:
                    reset = 0

                response["X-RateLimit-Limit"] = str(limit)
                response["X-RateLimit-Remaining"] = str(remaining)
                response["X-RateLimit-Reset"] = f"{reset}s"

                # We stop at the first relevant throttle to avoid header clutter
                break

        return response


class ThrottleHeadersMiddleware(MiddlewareMixin):
    """
    Add rate limit headers to all responses.
    Shows limits for the most restrictive throttle.
    """

    def process_response(self, request, response):
        if hasattr(request, "_throttled") and request._throttled:
            # Get the throttle that caused the throttling
            throttle = getattr(request, "_throttled_throttle", None)
            if throttle:
                response["X-RateLimit-Limit"] = throttle.get_rate()
                response["X-RateLimit-Remaining"] = 0
                response["X-RateLimit-Reset"] = throttle.wait()
                response["Retry-After"] = throttle.wait()

        return response
