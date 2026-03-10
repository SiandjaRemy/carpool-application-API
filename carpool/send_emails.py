from django.core.mail import send_mail
from django.conf import settings


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
        recipient_list=[
            email,
        ],
        fail_silently=False,  # Set to true in production once you've tested
    )
