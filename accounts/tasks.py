from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction

import logging

logger = logging.getLogger()


@shared_task()
def email_user(email, subject, message):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,  # Use settings
            recipient_list=[email],
            fail_silently=False,  # Set to true in production once you've tested
        )
        logger.info(f"email sucessfully sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        raise

    return "Done"