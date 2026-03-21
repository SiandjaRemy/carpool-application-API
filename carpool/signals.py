from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from carpool.models import Ride, RideRequest, Reservation, RideAlert
from carpool.views import (
    RideModelViewset,
    RideRequestModelViewset,
    ReservationModelViewset,
    RideAlertModelViewset,
)


@receiver([post_save, post_delete], sender=Ride)
def invalidate_ride_cache(sender, instance, **kwargs):
    """
    Whenever a Ride is saved or deleted, clear the relevant caches.
    Requires django-redis for delete_pattern to work.
    """
    # 1. Clear the list cache for everyone
    # (Since adding a new request changes the list view)
    RideModelViewset.invalidate_list_cache()

    # 2. Clear the specific item retrieve cache
    RideModelViewset.invalidate_retrieve_cache(pk=instance.pk)

    # 3. Clear custom action caches involving this user
    # Pass the passenger's ID so we only clear THEIR action cache, not everyone's
    RideRequestModelViewset.invalidate_action_cache(
        action_name="my_rides", user_id=instance.user.id
    )


@receiver([post_save, post_delete], sender=RideRequest)
def invalidate_ride_request_cache(sender, instance, **kwargs):
    """
    Whenever a RideRequest is saved or deleted, clear the relevant caches.
    Requires django-redis for delete_pattern to work.
    """
    # 1. Clear the list cache for everyone
    # (Since adding a new request changes the list view)
    RideRequestModelViewset.invalidate_list_cache()

    # 2. Clear the specific item retrieve cache
    RideRequestModelViewset.invalidate_retrieve_cache(pk=instance.pk)

    # 3. Clear custom action caches involving this user
    # Pass the passenger's ID so we only clear THEIR action cache, not everyone's
    RideRequestModelViewset.invalidate_action_cache(
        action_name="my_request", user_id=instance.passenger.id
    )


@receiver([post_save, post_delete], sender=Reservation)
def invalidate_ride_reservations_cache(sender, instance, **kwargs):
    """
    Whenever a Reservation is saved or deleted, clear the relevant caches.
    Requires django-redis for delete_pattern to work.
    """
    # 1. Clear the list cache for everyone
    # (Since adding a new request changes the list view)
    ReservationModelViewset.invalidate_list_cache()

    # 2. Clear the specific item retrieve cache
    ReservationModelViewset.invalidate_retrieve_cache(pk=instance.pk)


@receiver([post_save, post_delete], sender=RideAlert)
def invalidate_ride_alerts_cache(sender, instance, **kwargs):
    """
    Whenever a RideAlert is saved or deleted, clear the relevant caches.
    Requires django-redis for delete_pattern to work.
    """
    # 1. Clear the list cache for everyone
    # (Since adding a new request changes the list view)
    RideAlertModelViewset.invalidate_list_cache()

    # 2. Clear the specific item retrieve cache
    RideAlertModelViewset.invalidate_retrieve_cache(pk=instance.pk)
