from celery import shared_task
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings

from django.utils import timezone
from datetime import timedelta

import logging

from rides.models import Ride

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
