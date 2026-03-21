import hashlib
from functools import wraps
from django.core.cache import cache
from django.conf import settings
from rest_framework.response import Response


def cache_user_action(timeout: int = None):
    """Clean decorator to use on top of DRF @action methods"""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(viewset_instance, request, *args, **kwargs):
            # Fallback timeout
            actual_timeout = timeout or getattr(settings, "CACHE_TTL", 120)

            # Generate Key
            action_name = view_func.__name__
            user_id = (
                str(request.user.pk) if request.user.is_authenticated else "anonymous"
            )
            path = request.get_full_path()
            path_hash = hashlib.md5(path.encode("utf-8")).hexdigest()

            cache_key = f"viewset_cache_{viewset_instance.__class__.__name__}_{action_name}_{user_id}_{path_hash}"

            # Check Cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)

            # Execute view if miss
            response = view_func(viewset_instance, request, *args, **kwargs)

            if 200 <= response.status_code < 300:
                cache.set(cache_key, response.data, actual_timeout)
            return response

        return _wrapped_view

    return decorator


class CacheMixin:
    """
    Mixin to add caching capabilities to DRF ViewSets.
    Safely caches user-specific list and retrieve actions.
    """

    cache_timeout = getattr(settings, "CACHE_TTL", 120)

    def _get_user_id(self, request):
        return str(request.user.pk) if request.user.is_authenticated else "anonymous"

    def get_list_cache_key(self, request):
        path_hash = hashlib.md5(request.get_full_path().encode("utf-8")).hexdigest()
        return f"viewset_cache_{self.__class__.__name__}_list_{self._get_user_id(request)}_{path_hash}"

    def get_retrieve_cache_key(self, request, pk):
        return f"viewset_cache_{self.__class__.__name__}_retrieve_{pk}_{self._get_user_id(request)}"

    def list(self, request, *args, **kwargs):
        cache_key = self.get_list_cache_key(request)
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        if 200 <= response.status_code < 300:
            cache.set(cache_key, response.data, self.cache_timeout)
        return response

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        cache_key = self.get_retrieve_cache_key(request, pk)
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        response = super().retrieve(request, *args, **kwargs)
        if 200 <= response.status_code < 300:
            cache.set(cache_key, response.data, self.cache_timeout)
        return response

    # Invalidations

    def perform_update(self, serializer):
        """Automatically invalidate cache on successful update"""
        instance = serializer.save()
        self.invalidate_retrieve_cache(
            pk=instance.pk, user_id=self._get_user_id(self.request)
        )
        self.invalidate_list_cache(user_id=self._get_user_id(self.request))

    def perform_destroy(self, instance):
        """Automatically invalidate cache on successful delete"""
        pk = instance.pk
        instance.delete()
        self.invalidate_retrieve_cache(pk=pk, user_id=self._get_user_id(self.request))
        self.invalidate_list_cache(user_id=self._get_user_id(self.request))

    # Methods to invalidate via signals

    @classmethod
    def _get_base_cache_prefix(cls, action_name):
        """Internal helper to guarantee consistent prefix generation."""
        return f"viewset_cache_{cls.__name__}_{action_name}"

    @classmethod
    def _execute_invalidation(cls, prefix_string):
        """Safe invalidation execution."""
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(f"{prefix_string}*")
        else:
            import logging

            logging.getLogger(__name__).warning(
                f"Cache backend lacks delete_pattern. Cannot clear prefix: {prefix_string}"
            )

    @classmethod
    def invalidate_list_cache(cls, user_id=None):
        """
        Invalidates the 'list' cache.
        Pass user_id to only clear it for a specific user, or leave None to clear for everyone.
        """
        prefix = cls._get_base_cache_prefix("list")
        if user_id:
            prefix = f"{prefix}_{user_id}"
        cls._execute_invalidation(prefix)

    @classmethod
    def invalidate_retrieve_cache(cls, pk, user_id=None):
        """
        Invalidates the 'retrieve' cache for a specific object.
        """
        prefix = f"{cls._get_base_cache_prefix('retrieve')}_{pk}"
        if user_id:
            prefix = f"{prefix}_{user_id}"
        cls._execute_invalidation(prefix)

    @classmethod
    def invalidate_action_cache(cls, action_name, user_id=None):
        """
        Invalidates the cache for a custom @action (e.g., 'my_request').
        """
        prefix = cls._get_base_cache_prefix(action_name)
        if user_id:
            prefix = f"{prefix}_{user_id}"
        cls._execute_invalidation(prefix)
