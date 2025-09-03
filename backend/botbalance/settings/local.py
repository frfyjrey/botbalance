"""
Local development settings.
"""

from .base import *

# =============================================================================
# DEBUG SETTINGS
# =============================================================================

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# =============================================================================
# DATABASE
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "botbalance"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# =============================================================================
# CORS SETTINGS
# =============================================================================

CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins in development

# =============================================================================
# LOGGING
# =============================================================================

LOGGING["root"]["level"] = "DEBUG"
LOGGING["loggers"]["django"]["level"] = "INFO"  # Снижаем общий уровень Django
LOGGING["loggers"]["celery"]["level"] = "DEBUG"

# Включаем SQL запросы в DEBUG
LOGGING["loggers"]["django.db.backends"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}

# Отключаем сообщения о файлах и autoreload
LOGGING["loggers"]["django.utils.autoreload"] = {
    "handlers": ["console"],
    "level": "INFO",  # Поднимаем уровень чтобы не видеть DEBUG сообщения о файлах
    "propagate": False,
}

# Отключаем другие файловые DEBUG сообщения
LOGGING["loggers"]["django.core.management"] = {
    "handlers": ["console"],
    "level": "INFO",
    "propagate": False,
}

LOGGING["loggers"]["django.core.management.commands.runserver"] = {
    "handlers": ["console"],
    "level": "INFO",
    "propagate": False,
}

# =============================================================================
# DEVELOPMENT TOOLS
# =============================================================================

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Cache - use local memory cache for development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Static files
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
