from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction


@shared_task()
def email_user(email, subject, message):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,  # Use settings
        recipient_list=[email],
        fail_silently=False,  # Set to true in production once you've tested
    )
