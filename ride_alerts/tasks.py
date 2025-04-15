from __future__ import absolute_import, unicode_literals

from celery import shared_task

from django.utils import timezone
from datetime import timedelta

import logging

from ride_alerts.models import RideAlert
from rides.models import Ride
from utils.send_emails import alert_users_via_email


logger = logging.getLogger("background")


@shared_task(name="alert_users_for_ride")
def alert_users_for_ride(ride_id):
    today = timezone.now()
    ride = Ride.objects.filter(
        id=ride_id, is_active=True, departure_datetime__gte=today
    ).first()
    
    if ride is not None:

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
                # alert_users_via_email(emails=user_mails, subject=subject, message=message) # Comment when working offline
                logger.info(f"Emails successfully sent to {len(user_mails)} users")
            except Exception as e:
                logger.error(f"Failed to send emails: {str(e)}")
                raise
        else:
            return "No active alerts found"
    else:
        return "Corresponding ride does not exist"
    return "Done"
