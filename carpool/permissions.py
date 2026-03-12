from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsCreatorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        return obj.user == user


class IsCreator(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        return obj.user == user


class IsRideOwner(BasePermission):
    """
    Custom permission to only allow owners of a ride to access/accept/reject requests.
    """

    def has_permission(self, request, view):
        # Check if user is authenticated
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # For nested routes, obj might be a RideRequest
        # We need to check if the user owns the related ride

        # If we're dealing with a RideRequest, check the ride's owner
        if hasattr(obj, "ride"):
            return obj.ride.user == request.user
        # If we're dealing with a Ride directly
        elif hasattr(obj, "user"):
            return obj.user == request.user
        return False


class IsRequestOwner(BasePermission):
    """
    Custom permission to only allow the passenger who created the request to cancel it.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Check if the user is the passenger who made the request
        return obj.passenger == request.user


class IsRequestOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow the passenger who created the request to cancel it.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # Check if the user is the passenger who made the request
        return obj.passenger == request.user


class IsRequestPending(BasePermission):
    """
    Custom permission to only allow actions on pending requests.
    """

    def has_object_permission(self, request, view, obj):
        from carpool.enums.enums import RequestStatus

        return obj.status == RequestStatus.PENDING
