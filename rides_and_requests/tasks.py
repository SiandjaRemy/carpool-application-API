from celery import shared_task
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

import logging

from rides_and_requests.models import Ride, RideAlert

logger = logging.getLogger("rides_and_requests")

def alert_user_via_email(emails, subject, message):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,  # Use settings
        recipient_list=emails,
        fail_silently=False,  # Set to true in production once you've tested
    )


@shared_task(name="alert_users_for_ride")
def alert_users_for_ride(ride_id):
    today = timezone.now()
    try:
        ride = Ride.objects.filter(id=ride_id, is_active=True, departure_datetime__gte=today).first()
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
        subject = "Your ride alrt has just been triggered"
        message = f"Hello, a ride from {ride.departure_town} to {ride.arrival_town} on {ride.departure_datetime} was just created, check it out"
        user_mails = []
        for alert in list(alerts):
            user_mails.append(alert.user.email)
            print(f"Hey {alert.user}, a ride from {alert.departure_town} to {alert.arrival_town} on {ride.departure_datetime} was just created")
        try:
            alert_user_via_email(emails=user_mails, subject=subject, message=message)
            logger.info(f"Emails successfully sent to {len(user_mails)} users")
        except Exception as e:
            logger.error(f"Failed to send emails: {str(e)}")
            raise
    else:
        print("No alerts found")
    return "Done"



