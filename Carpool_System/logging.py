import os
from pathlib import Path
from datetime import datetime

from django.conf import settings


BASE_DIR = Path(__file__).resolve().parent.parent  # Project root directory

LOG_DIR = BASE_DIR / "logs"  # Central log directory
APP_LOG_DIR = LOG_DIR / "app_logs"  # App log directory
SECURITY_LOG_DIR = LOG_DIR / "security_logs"  # Security log directory
ERROR_LOG_DIR = LOG_DIR / "error_logs"  # Error log directory

os.makedirs(APP_LOG_DIR, exist_ok=True)  # Ensure directory exists
os.makedirs(SECURITY_LOG_DIR, exist_ok=True)  # Ensure directory exists
os.makedirs(ERROR_LOG_DIR, exist_ok=True)  # Ensure directory exists

CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")  # Current date for log rotation

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        # Only allows logs when DEBUG = False (production)
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        # Only allows logs when DEBUG = True (development)
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
        # Custom filter: Adds request context (user, IP, request ID) to logs
        "request_context": {
            "()": "Carpool_System.logging_filters.RequestContextFilter",
        },
    },
    "formatters": {
        # Verbose format: Human-readable with lots of details
        "verbose": {
            "format": "[{levelname}] {asctime} {process:d} {thread:d} {name}:{lineno} - {message}",
            "style": "{",
        },
        # JSON format: Structured logs for production (easily parsed by log aggregators)
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "fmt": """  # JSON structure with contextual data
            {
                "timestamp": "%(asctime)s",
                "level": "%(levelname)s",
                "service": "%(name)s",
                "module": "%(module)s",
                "function": "%(funcName)s",
                "line": %(lineno)d,
                "message": "%(message)s",
                "request_id": "%(request_id)s",  # Added by RequestContextFilter
                "user": "%(user)s",              # Added by RequestContextFilter
                "ip": "%(ip)s"                   # Added by RequestContextFilter
            }
            """,
        },
        # Simple format: Basic info for development console
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        # Console handler for development (DEBUG mode only)
        "console": {
            "level": "DEBUG",  # Log level
            "filters": ["require_debug_true"],  # Only in DEBUG mode
            "class": "logging.StreamHandler",  # Output to terminal
            "formatter": "verbose",  # Simple human-readable format
        },
        # Console handler for production (JSON format)
        "production_console": {
            "level": "INFO",
            "filters": [
                "require_debug_false",
                "request_context",
            ],  # Production + context
            "class": "logging.StreamHandler",
            "formatter": "json",  # JSON format for log aggregators
        },
        # Rotating file handler for application logs (50MB max, 5 backups)
        "app_file": {
            "level": "INFO",
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",  # Thread-safe
            "filename": APP_LOG_DIR / f"app_{CURRENT_DATE}.log",
            "maxBytes": 1024 * 1024 * 50,  # 50 MB per file
            "backupCount": 5,  # Keep 5 backup files
            "formatter": "json",
            "encoding": "utf8",
            "filters": ["request_context"],  # Add request context
        },
        # Dedicated error log file
        "error_file": {
            "level": "ERROR",  # Only ERROR level and above
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",  # Thread-safe
            "filename": ERROR_LOG_DIR / f"error_{CURRENT_DATE}.log",
            "maxBytes": 1024 * 1024 * 20,  # 20 MB
            "backupCount": 5,
            "formatter": "verbose",  # Verbose format for debugging errors
            "encoding": "utf8",
            "filters": ["request_context"],
        },
        # Security-specific log file
        "security_file": {
            "level": "WARNING",  # WARNING and above (security concerns)
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": SECURITY_LOG_DIR / f"security_{CURRENT_DATE}.log",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 3,
            "formatter": "json",
            "encoding": "utf8",
            "filters": ["request_context"],
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": False,  # Security: don't include HTML in emails
            "formatter": "json",
        },
    },
    "loggers": {
        # Django security logs (CSRF, XSS, etc.)
        "django.security": {
            "handlers": ["security_file", "mail_admins"],  # Security file + email
            "level": "WARNING",  # WARNING and above
            "propagate": False,
        },
        # HTTP request errors (404, 500, etc.)
        "django.request": {
            "handlers": [
                "console",
                "error_file",
                "mail_admins",
            ],  # Error file + email admins
            "level": "ERROR",  # Only ERROR level
            # "level": "CRITICAL",
            "propagate": False,
        },
        # Django development server logs
        "django.server": {
            "handlers": ["console", "error_file"],
            "level": "DEBUG" if settings.DEBUG else "ERROR",  # More verbose in DEBUG
            "propagate": False,
        },
        # YOUR APPLICATION'S LOGS (most important)
        "app": {
            "handlers": ["app_file", "production_console"],
            "level": "DEBUG" if settings.DEBUG else "INFO",  # More verbose in DEBUG
            "propagate": False,
        },
        # Celery task logs
        "celery": {
            "handlers": ["app_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
