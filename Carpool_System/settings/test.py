import dj_database_url

from .base import *
import os

import mimetypes

mimetypes.add_type("application/javascript", ".js")

SECRET_KEY = "django-insecure-2@6qm0mn7=k&y-s7d=^$625*$(3)hx^)73i_ee4r*f2194)3#v"


ALLOWED_HOSTS = ["*"]

if DEBUG:
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
else:
    # Use postgres db for more realistic tests
    DATABASE_URL = os.getenv("TEST_DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set for testing")

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,
            ssl_require=True,
        )
    }


# Use faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Local Cache / Redis
REDIS_URL = os.environ.get("LOCAL_REDIS_INSTANCE_URL")


# Cache for tests
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

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
