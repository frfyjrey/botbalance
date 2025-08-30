"""
Production settings for GCP deployment.

Optimized for:
- Google Cloud SQL (PostgreSQL)
- Google App Engine / Cloud Run
- Google Cloud Storage for static files
- Redis for caching and Celery
"""

import dj_database_url

from .base import *

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

DEBUG = False

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# =============================================================================
# HOSTS AND CORS
# =============================================================================

ALLOWED_HOSTS = [
    "api.domain.com",  # Replace with your API domain
    ".appspot.com",  # Google App Engine
    ".a.run.app",  # Cloud Run
] + os.getenv("ALLOWED_HOSTS", "").split(",")

CORS_ALLOWED_ORIGINS = [
    "https://app.domain.com",  # Replace with your frontend domain
    "https://domain.com",  # Main domain
] + os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")

CORS_ALLOW_ALL_ORIGINS = False

# =============================================================================
# DATABASE
# =============================================================================

# Support for Cloud SQL via DATABASE_URL
if "DATABASE_URL" in os.environ:
    DATABASES["default"] = dj_database_url.parse(os.environ.get("DATABASE_URL"))
else:
    # Manual Cloud SQL configuration
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),  # Cloud SQL instance connection name
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {
                "sslmode": "require",
            },
        }
    }

# Connection pooling
DATABASES["default"]["CONN_MAX_AGE"] = 60

# =============================================================================
# STATIC FILES (Google Cloud Storage)
# =============================================================================

# Configure for Google Cloud Storage
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files (if needed)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# =============================================================================
# CACHING (Redis)
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/1"),
        "KEY_PREFIX": "boilerplate",
        "TIMEOUT": 300,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 20,
                "retry_on_timeout": True,
            },
        },
    }
}

# =============================================================================
# CELERY FOR PRODUCTION
# =============================================================================

# Use Redis for broker and results
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Production Celery settings
CELERY_WORKER_CONCURRENCY = int(os.getenv("CELERY_CONCURRENCY", "2"))
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# =============================================================================
# LOGGING FOR PRODUCTION
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if os.getenv("JSON_LOGS") else "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =============================================================================
# EMAIL SETTINGS
# =============================================================================

# Configure for SendGrid, Mailgun, or Google Cloud Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@domain.com")

# =============================================================================
# PERFORMANCE SETTINGS
# =============================================================================

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Template caching
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    ),
]
