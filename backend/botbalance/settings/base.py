"""
Django settings for botbalance project.

Base settings shared across all environments.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from project root .env
load_dotenv(BASE_DIR.parent / ".env")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


# Application definition

INSTALLED_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    # Local apps - using explicit AppConfig paths for enterprise reliability
    "botbalance.api.apps.ApiConfig",
    "botbalance.core.apps.CoreConfig",
    "botbalance.tasks.apps.TasksConfig",
    "botbalance.exchanges.apps.ExchangesConfig",
    "strategies.apps.StrategiesConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "botbalance.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "botbalance.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

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


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =============================================================================
# BOTBALANCE SETTINGS
# =============================================================================

# Exchange environment: mock | live (simplified from 4 to 2 options)
EXCHANGE_ENV = os.getenv("EXCHANGE_ENV", "mock").lower()

# Smoke tests for development (disabled by default, enabled only locally)
ENABLE_SMOKE_TESTS = os.getenv("ENABLE_SMOKE_TESTS", "false").lower() == "true"

# Pricing service configuration
PRICING_SOURCE = os.getenv("PRICING_SOURCE", "mid").lower()  # mid | last
PRICING_USE_CACHE = os.getenv("PRICING_USE_CACHE", "true").lower() == "true"
PRICING_TTL_SECONDS = int(os.getenv("PRICING_TTL_SECONDS", "300"))
PRICING_BYPASS_TESTNET_ALLOWLIST = (
    os.getenv("PRICING_BYPASS_TESTNET_ALLOWLIST", "true").lower() == "true"
)

# Portfolio state configuration
PORTFOLIO_STATE_COOLDOWN_SEC = int(os.getenv("PORTFOLIO_STATE_COOLDOWN_SEC", "5"))

# Optional system testnet account (only used when EXCHANGE_ENV=live and enabled)
ENABLE_SYSTEM_TESTNET_ACCOUNT = (
    os.getenv("ENABLE_SYSTEM_TESTNET_ACCOUNT", "false").lower() == "true"
)
BINANCE_SPOT_TESTNET_API_KEY = os.getenv("BINANCE_SPOT_TESTNET_API_KEY", "")
BINANCE_SPOT_TESTNET_API_SECRET = os.getenv("BINANCE_SPOT_TESTNET_API_SECRET", "")

# Order polling (Step 5): disabled by default; enable together with EXCHANGE_ENV=live
ENABLE_ORDER_POLLING = os.getenv("ENABLE_ORDER_POLLING", "false").lower() == "true"

# Binance testnet active symbols allowlist (CSV)
BINANCE_TESTNET_ACTIVE_SYMBOLS = os.getenv(
    "BINANCE_TESTNET_ACTIVE_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT"
)

# =============================================================================
# DJANGO REST FRAMEWORK
# =============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# =============================================================================
# JWT AUTHENTICATION
# =============================================================================

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
}


# =============================================================================
# CORS SETTINGS
# =============================================================================

CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in debug mode


# =============================================================================
# CELERY SETTINGS
# =============================================================================

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Task settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Beat Schedule for periodic tasks
CELERY_BEAT_SCHEDULE = {
    "poll-orders": {
        "task": "botbalance.tasks.tasks.poll_orders_task",
        "schedule": 30.0,  # Every 30 seconds
        "options": {
            "expires": 25
        },  # Task expires in 25 seconds to prevent accumulation
    },
    "strategy-tick": {
        "task": "botbalance.tasks.tasks.strategy_tick_task",
        "schedule": 30.0,  # Every 30 seconds
        "options": {
            "expires": 25
        },  # Task expires in 25 seconds to prevent accumulation
    },
}


# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
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
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =============================================================================
# CONNECTOR HEALTH MONITORING
# =============================================================================

# Time window in seconds for considering a connector healthy
CONNECTOR_HEALTH_WINDOW_SEC = int(os.getenv("CONNECTOR_HEALTH_WINDOW_SEC", "60"))


# =============================================================================
# AUTO TRADE SETTINGS
# =============================================================================

# Global flag to enable automatic trading (Step 6)
ENABLE_AUTO_TRADE = os.getenv("ENABLE_AUTO_TRADE", "false").lower() == "true"
