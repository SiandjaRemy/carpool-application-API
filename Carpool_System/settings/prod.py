from .base import *
import os
import dj_database_url


SECRET_KEY = os.environ.get("SECRET_KEY")

# Overide just to be sure
DEBUG = False


# Parse allowed hosts from environment variable
ALLOWED_HOSTS_ENV = os.getenv("ALLOWED_HOSTS", "")
if ALLOWED_HOSTS_ENV:
    ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_ENV.split(",")]
else:
    # Or raise an error to force configuration
    raise ValueError("ALLOWED_HOSTS environment variable is required in production")

CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]


SIMPLE_JWT = SIMPLE_JWT.copy()
SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY


# Database (Render)
DATABASE_URL = os.getenv("DATABASE_SERVICE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in production")

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=60,
        ssl_require=True,
    )
}

# Local Cache / Redis
REDIS_URL = os.environ.get("REDIS_INSTANCE_URL")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 1000,
                "retry_on_timeout": True,
                "health_check_interval": 30,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        },
        "KEY_PREFIX": "api_prod",
        "TIMEOUT": 300,
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
