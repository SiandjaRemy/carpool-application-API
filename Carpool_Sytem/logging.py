import os
from pathlib import Path
from datetime import datetime

from django.conf import settings


BASE_DIR = Path(__file__).resolve().parent.parent  # Project root directory
DEBUG = settings.DEBUG  # Use Django's DEBUG setting

LOG_DIR = BASE_DIR / "logs"  # Central log directory
APP_LOG_DIR = LOG_DIR / "app_logs"  # App log directory
ERROR_LOG_DIR = LOG_DIR / "error_logs"  # Error log directory

os.makedirs(APP_LOG_DIR, exist_ok=True)  # Ensure directory exists
os.makedirs(ERROR_LOG_DIR, exist_ok=True)  # Ensure directory exists

CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")  # Current date for log rotation

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
            "filename": APP_LOG_DIR / f"app_{CURRENT_DATE}.log",
            "formatter": "verbose",
        },
        "error_file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": ERROR_LOG_DIR / f"error_{CURRENT_DATE}.log",
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
