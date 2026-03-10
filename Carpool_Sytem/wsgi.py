"""
WSGI config for Carpool_Sytem project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Use environment variable to determine settings
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    (
        "Carpool_Sytem.settings.prod"
        if os.environ.get("DJANGO_ENV") == "production"
        else "Carpool_Sytem.settings.dev"
    ),
)

application = get_wsgi_application()
