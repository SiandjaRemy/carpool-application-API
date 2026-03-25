from .base import *
import os

import mimetypes

mimetypes.add_type("application/javascript", ".js")

SECRET_KEY = "django-insecure-2@6qm0mn7=k&y-s7d=^$625*$(3)hx^)73i_ee4r*f2194)3#v"

# Overide just to be sure
DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use fast in-memory database for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {
            "NAME": ":memory:",
        },
    }
}


# Use faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Local Cache / Redis
REDIS_URL = os.environ.get("LOCAL_REDIS_INSTANCE_URL")


# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


# Celery (Dev)
CELERY_BROKER_URL = REDIS_URL

# Email (Console backend for testing)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST")  # Kept to avoid import errors if ref'd
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL")

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
]
