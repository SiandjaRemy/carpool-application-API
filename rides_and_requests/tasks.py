from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings

from django.utils import timezone
from datetime import timedelta

import logging

from rides_and_requests.models import Ride, RideAlert

logger = logging.getLogger("rides_and_requests")


def alert_users_via_email(emails, subject, message):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,  # Use settings
        recipient_list=emails,
        fail_silently=False,  # Set to true in production once you've tested
    )

def alert_a_user_via_email(email, subject, message):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,  # Use settings
        recipient_list=[email,],
        fail_silently=False,  # Set to true in production once you've tested
    )


@shared_task(name="alert_users_for_ride")
def alert_users_for_ride(ride_id):
    today = timezone.now()
    try:
        ride = Ride.objects.filter(
            id=ride_id, is_active=True, departure_datetime__gte=today
        ).first()
    except Exception as e:
        raise ValidationError(str(e))

    alerts = RideAlert.objects.select_related("user").filter(
        is_active=True,
        departure_datetime__gte=today,
        departure_town=ride.departure_town,
        arrival_town=ride.arrival_town,
        available_seats__lte=ride.available_seats,
    )
    if alerts is not None:
        subject = "Your ride alert has just been triggered"
        message = f"Hello, a ride from {ride.departure_town} to {ride.arrival_town} on {ride.departure_datetime} was just created, check it out"
        user_mails = []
        for alert in list(alerts):
            user_mails.append(alert.user.email)
            print(
                f"Hey {alert.user}, a ride from {alert.departure_town} to {alert.arrival_town} on {ride.departure_datetime} was just created"
            )
        try:
            alert_users_via_email(emails=user_mails, subject=subject, message=message)
            logger.info(f"Emails successfully sent to {len(user_mails)} users")
        except Exception as e:
            logger.error(f"Failed to send emails: {str(e)}")
            raise
    else:
        return "No active alerts found"
    return "Done"


# Create a periodic task that will be triggered every 5 minutes and will update the active status of all instances with dates in the past


@shared_task(name="rides_and_requests.tasks.deactivate_expired_rides")
def deactivate_expired_rides():
    
    # Calculate threshold time (10 minutes from now)
    threshold_time = timezone.now() + timedelta(minutes=10)

    # Get rides that are active AND have departure time <= threshold
    expired_rides = Ride.objects.select_related("user").filter(
        is_active=True,
        departure_datetime__lte=threshold_time
    ).order_by("-created_at")
    
    if expired_rides.exists():
        # Process rides in chunks to avoid memory issues
        chunk_size = 100
        for i in range(0, len(expired_rides), chunk_size):
            chunk = expired_rides[i:i + chunk_size]
            
            # Update rides in bulk
            Ride.objects.filter(id__in=[ride.id for ride in chunk]).update(
                is_active=False,
                modified_at=timezone.now()  # Fix typo in model field
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
                    alert_a_user_via_email(
                        email=ride.user.email,
                        subject=subject,
                        message=message
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification for ride {ride.id}: {str(e)}")
    
    else:
        return "No expired rides found"

    return f"Deactivated {len(expired_rides)} expired rides"

