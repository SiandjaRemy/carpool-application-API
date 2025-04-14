from __future__ import absolute_import, unicode_literals

from celery import shared_task

from django.utils import timezone
from datetime import timedelta

import logging

from rides.models import Ride
from utils.send_emails import alert_a_user_via_email

logger = logging.getLogger("background")


# A periodic task that will be triggered every 5 minutes and will update the active status of all instances with dates in the past


@shared_task(name="rides.tasks.deactivate_expired_rides")
def deactivate_expired_rides():
    # Calculate threshold time (10 minutes from now)
    threshold_time = timezone.now() + timedelta(minutes=10)

    # Get rides that are active AND have departure time <= threshold
    expired_rides = (
        Ride.objects.select_related("user")
        .filter(is_active=True, departure_datetime__lte=threshold_time)
        .order_by("-created_at")
    )

    if expired_rides.exists():
        # Process rides in chunks to avoid memory issues
        chunk_size = 100
        for i in range(0, len(expired_rides), chunk_size):
            chunk = expired_rides[i : i + chunk_size]

            # Update rides in bulk
            Ride.objects.filter(id__in=[ride.id for ride in chunk]).update(
                is_active=False, modified_at=timezone.now()  # Fix typo in model field
            )

            # Send emails for this chunk
            for ride in chunk:
                subject = f"Your ride from {ride.departure_town} to {ride.arrival_town} is approaching"
                message = (
                    f"Hey {ride.user.username},\n\n"
                    f"This is a reminder that your ride from {ride.departure_town} "
                    f"to {ride.arrival_town} is scheduled to depart within the next 10 minutes.\n\n"
                    f"Departure Town: {ride.departure_town}\n"
                    f"Arrival Town: {ride.arrival_town}\n"
                    f"Departure Time: {ride.departure_datetime.strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"The ride will be marked as inactive shortly."
                )

                try:
                    # # Comment when working offline
                    # alert_a_user_via_email(
                    #     email=ride.user.email,
                    #     subject=subject,
                    #     message=message
                    # )
                    print(message)
                except Exception as e:
                    logger.error(
                        f"Failed to send notification for ride {ride.id}: {str(e)}"
                    )

    else:
        return "No expired rides found"

    return f"Deactivated {len(expired_rides)} expired rides"
