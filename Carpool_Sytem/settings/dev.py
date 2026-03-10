from .base import *
import os

import mimetypes

mimetypes.add_type("application/javascript", ".js")

# Overide just to be sure
DEBUG = True

ALLOWED_HOSTS = ["*"]

# Local Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # "NAME": BASE_DIR / "db.sqlite3",
        "NAME": "db.sqlite3",
    }
}


# Local Cache / Redis
REDIS_URL = os.environ.get("LOCAL_REDIS_INSTANCE_URL")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 1000,  # Allow many concurrent connections
                "retry_on_timeout": True,  # Improve reliability
                "health_check_interval": 30,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,  # Fail fast on network issues
            "SOCKET_TIMEOUT": 5,  # Avoid hanging cache calls
            "IGNORE_EXCEPTIONS": True,
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        },
        "KEY_PREFIX": "api_dev",  # e.g. "api_dev"  # Namespacing for safety (especially if sharing Redis)
        "TIMEOUT": 300,  # Default cache timeout (5 minutes)
    }
}

# Channels (Dev)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

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

INTERNAL_IPS = ["127.0.0.1"]
