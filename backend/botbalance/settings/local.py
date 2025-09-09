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

# Включаем DEBUG для Exchange адаптеров
LOGGING["loggers"]["botbalance.exchanges"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}

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

# Включаем логирование HTTP запросов
LOGGING["loggers"]["django.request"] = {
    "handlers": ["console"],
    "level": "INFO",  # Показываем все HTTP запросы
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


# ВАЖНО: Переопределяем переменные окружения для разработки OKX
import os

os.environ["EXCHANGE_ENV"] = "live"  # mock | live
os.environ["ENABLE_AUTO_TRADE"] = "true"  # Включаем auto-trade для разработки
os.environ["ENABLE_SMOKE_TESTS"] = "true"  # Включаем smoke тесты для разработки
os.environ["ENABLE_ORDER_POLLING"] = "true"  # Включаем polling для разработки.в


# =============================================================================
# JWT SETTINGS FOR DEVELOPMENT (longer sessions to avoid frequent logouts)
# =============================================================================

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),  # 8 часов для разработки
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),  # 30 дней для разработки
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

# =============================================================================
# SESSION SETTINGS FOR DEVELOPMENT (prevent HMR logout issues)
# =============================================================================

SESSION_COOKIE_AGE = 28800  # 8 часов в секундах
SESSION_SAVE_EVERY_REQUEST = True  # Обновлять сессию при каждом запросе
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Не истекать при закрытии браузера
SESSION_COOKIE_SECURE = False  # Для localhost HTTP
CSRF_COOKIE_SECURE = False  # Для localhost HTTP
