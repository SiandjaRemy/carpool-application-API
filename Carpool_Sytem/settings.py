"""
Django settings for Carpool_Sytem project.

Generated by 'django-admin startproject' using Django 5.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()


import mimetypes

mimetypes.add_type("application/javascript", ".js")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", default=False)

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    
    "accounts",

    "rides",
    "ride_alerts",
    "ride_requests",
    "passengers",
    "utils",
    
    
    "drf_yasg",
    "rest_framework_simplejwt.token_blacklist",
    "rest_framework",
    "django_celery_beat",
    "django_celery_results",
    "debug_toolbar",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",  # Debug toolbar
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

REST_FRAMEWORK = {
    # "NON_FIELD_ERRORS_KEY":"errors",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=48),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=8),
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Token",),
    "TOKEN_OBTAIN_SERIALIZER": "accounts.serializers.MyTokenObtainPairSerializer",
}


SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Basic": {"type": "basic"},
        "Token": {"type": "apiKey", "name": "Authorization", "in": "header"},
    }
}


DJOSER = {
    "ACTIVATION_URL": "#/activate/{uid}/{token}",
    "SEND_ACTIVATION_EMAIL": False,
    "SERIALIZERS": {
        "user": "accounts.serializers.UserDataSerializer",
        "current_user": "accounts.serializers.UserDataSerializer",
    },
}

# Setting for the expiratory time of the password reset token
# PASSWORD_RESET_TIMEOUT = 60 * 5 # 5 minutes
PASSWORD_RESET_TIMEOUT = 60 * 10  # 10 minutes

ROOT_URLCONF = "Carpool_Sytem.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Carpool_Sytem.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_INSTANCE_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}


if not DEBUG:

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime:s} {name} {module}.py (line {lineno:d}) {funcName} {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {asctime:s} {name} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
            "file": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "filename": BASE_DIR / "django_api.log",
                "formatter": "verbose",
            },
            "error_file": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "filename": BASE_DIR / "django_api.log",
                "formatter": "verbose",
            },
            "mail_admins": {
                "level": "ERROR",
                "filters": ["require_debug_false"],
                "class": "django.utils.log.AdminEmailHandler",
                "include_html": True,
                "formatter": "verbose",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console", "error_file", "mail_admins"],
                "level": "ERROR",
                "propagate": False,
            },
            "django": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": True,
            },
            "background": {
                "handlers": ["file", "mail_admins"],
                "level": "ERROR",
                "propagate": False,
            },
        },
    }



# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

# TIME_ZONE = "UTC"
TIME_ZONE = "Africa/Douala"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_TIMEOUT = 300
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL")

MAIN_ADMIN_NAME = os.environ.get("MAIN_ADMIN_NAME")
MAIN_ADMIN_EMAIL = os.environ.get("MAIN_ADMIN_EMAIL")

ADMINS = [(MAIN_ADMIN_NAME, MAIN_ADMIN_EMAIL)]


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"


INTERNAL_IPS = [
    "127.0.0.1",
]

FRONTEND_URL = os.environ.get("FRONTEND_URL")

# Celery Configuration Options
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Celery Configuration
CELERY_BROKER_URL = os.environ.get("REDIS_INSTANCE_URL_2")
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Douala"  # Set your desired timezone

# Celery Beat Configuration (for periodic tasks)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"

# CELERY RESULTS SETTINGS
CELERY_RESULT_BACKEND = "django-db"  # To store task results in the Django database
CELERY_RESULT_SERIALIZER = "json"

broker_connection_retry_on_startup = True
