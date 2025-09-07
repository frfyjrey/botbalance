"""
Production settings for GCP deployment.

Optimized for:
- Google Cloud SQL (PostgreSQL)
- Google App Engine / Cloud Run
- Google Cloud Storage for static files
- Redis for caching and Celery
"""

import os

from .base import *

# =============================================================================
# MIDDLEWARE FOR PRODUCTION
# =============================================================================

# Insert whitenoise after SecurityMiddleware for static files serving
MIDDLEWARE = (
    [
        "corsheaders.middleware.CorsMiddleware",
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",  # Add whitenoise for static files
    ]
    + MIDDLEWARE[2:]
)  # Add the rest of middleware from base.py

# =============================================================================
# LOGGING
# =============================================================================

# Minimal logging to avoid JSON formatter issues
LOGGING_CONFIG = None  # Disable Django's logging configuration
LOGGING = {}

# Production templates with caching for performance
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": False,  # Must be False when loaders is defined
        "OPTIONS": {
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ],
                ),
            ],
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

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
    "api.botbalance.me",  # Production API domain
    ".appspot.com",  # Google App Engine
    ".run.app",  # Cloud Run (fixed pattern)
]

# Add additional allowed hosts from environment variable if set
if os.getenv("ALLOWED_HOSTS"):
    ALLOWED_HOSTS.extend(
        host.strip()
        for host in os.getenv("ALLOWED_HOSTS", "").split(",")
        if host.strip()
    )

CORS_ALLOWED_ORIGINS = [
    "https://app.botbalance.me",  # Frontend domain
    "https://botbalance.me",  # Main domain
]

# Add additional CORS origins from environment variable if set
if os.getenv("CORS_ALLOWED_ORIGINS"):
    CORS_ALLOWED_ORIGINS.extend(
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    )

CORS_ALLOW_ALL_ORIGINS = False

# =============================================================================
# DATABASE
# =============================================================================

# Support for Cloud SQL via separate secrets
if all(key in os.environ for key in ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),  # Cloud SQL Unix socket
        "PORT": "",  # No port for Unix socket
        "OPTIONS": {},
    }
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
STATIC_ROOT = BASE_DIR / "staticfiles"

# Whitenoise settings for serving static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (if needed)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# CACHING (Redis)
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://localhost:6379/1"),
        "KEY_PREFIX": "botbalance",
        "TIMEOUT": 300,
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

# Reduce idle BRPOP churn on Redis while keeping immediate task pickup
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "brpop_timeout": int(os.getenv("CELERY_BROKER_BRPOP_TIMEOUT", "60")),
}

# Beat Schedule for periodic tasks (same as base.py)
CELERY_BEAT_SCHEDULE = {
    "poll-orders": {
        "task": "botbalance.tasks.tasks.poll_orders_task",
        "schedule": 30.0,  # Every 30 seconds
        "options": {
            "expires": 25
        },  # Task expires in 25 seconds to prevent accumulation
    },
}

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
        # Отключаем сообщения о файлах и autoreload в production тоже
        "django.utils.autoreload": {
            "handlers": ["console"],
            "level": "WARNING",  # В продакшене еще выше уровень
            "propagate": False,
        },
        "django.core.management": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.core.management.commands.runserver": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # SQL запросы в продакшене обычно не нужны, но если нужно - можно включить
        # "django.db.backends": {
        #     "handlers": ["console"],
        #     "level": "DEBUG",
        #     "propagate": False,
        # },
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

# Template caching already configured above in TEMPLATES definition

# =============================================================================
# ОБРАБОТКА СБОЕВ ВНЕШНЕГО API: используем testnet для тестирования resilience
# =============================================================================
# Безопасные fallback настройки (переопределяются через переменные окружения на продакшене)
EXCHANGE_ENV = "mock"  # Fallback на mock (безопасно)

# =============================================================================
# JWT SETTINGS FOR PRODUCTION (secure session timing)
# =============================================================================

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),  # 2 часа для production
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),  # 7 дней для production
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

# =============================================================================
# SESSION SETTINGS FOR PRODUCTION
# =============================================================================

SESSION_COOKIE_AGE = 7200  # 2 часа в секундах
SESSION_SAVE_EVERY_REQUEST = True  # Обновлять сессию при каждом запросе
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Не истекать при закрытии браузера
