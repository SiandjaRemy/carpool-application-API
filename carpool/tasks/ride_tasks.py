from celery import shared_task

from django.utils import timezone
from datetime import timedelta

import logging

from carpool.enums.enums import RideStatus
from carpool.models.ride import Ride
from carpool.send_emails import alert_a_user_via_email


logger = logging.getLogger("background")


# A periodic task that will be triggered every 5 minutes and will update the status of all instances with dates in the next 10 minutes
@shared_task(name="rides.tasks.update_ride_statuses")
def update_ride_statuses():
    # Calculate threshold time (10 minutes from now)
    threshold_time = timezone.now() + timedelta(minutes=10)

    # Get rides with status SCHEDULED AND departure time <= threshold
    upcoming_rides = (
        Ride.objects.select_related("user")
        .filter(status=RideStatus.SCHEDULED, departure_datetime__lte=threshold_time)
        .order_by("-created_at")
    )

    if upcoming_rides.exists():
        id_list = [ride.id for ride in upcoming_rides]
        # Update rides in bulk
        Ride.objects.filter(id__in=id_list).update()

        # Send emails for this expired_rides
        for ride in upcoming_rides:
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
                # Comment when working offline
                alert_a_user_via_email(
                    email=ride.user.email, subject=subject, message=message
                )
                print(message)
            except Exception as e:
                logger.error(
                    f"Failed to send notification for ride {ride.id}: {str(e)}"
                )

    else:
        return "No expired rides found"

    return f"Deactivated {len(upcoming_rides)} expired rides"
