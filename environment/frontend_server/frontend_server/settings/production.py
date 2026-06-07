"""
Production Django settings for frontend_server.

This file extends the base settings with production-specific configurations.
To use: set DJANGO_SETTINGS_MODULE=frontend_server.settings.production
"""
import os
from .base import *

# =============================================================================
# Security Settings
# =============================================================================

# SECURITY WARNING: use a unique, unpredictable secret key in production!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'CHANGE-THIS-IN-PRODUCTION')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in {'true', '1', 'yes'}

# Allowed hosts - set via environment variable (comma-separated)
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# =============================================================================
# CORS Configuration for External Agent API Access
# =============================================================================

# Allow CORS for API endpoints
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL', 'False').lower() in {'true', '1', 'yes'}

# Alternatively, whitelist specific origins
CORS_ALLOWED_ORIGINS = [
    origin.strip() 
    for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') 
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-api-key',
]

# =============================================================================
# Database Configuration (PostgreSQL for production)
# =============================================================================

if os.getenv('DATABASE_URL'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'reverie'),
            'USER': os.getenv('DB_USER', 'reverie'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# =============================================================================
# Static Files Configuration
# =============================================================================

# Static files will be served by Nginx in production
STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'staticfiles')

# Simplified static file serving (if not using Nginx)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# =============================================================================
# Security Middleware Settings
# =============================================================================

# HTTPS settings
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in {'true', '1', 'yes'}
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Session security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# Content security
SECURE_CONTENT_TYPE_NOSNIFF = True
# Note: SECURE_BROWSER_XSS_FILTER is deprecated since Django 3.0
# Modern browsers have removed XSS auditor functionality
X_FRAME_OPTIONS = 'DENY'

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# =============================================================================
# Logging Configuration
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.getenv('LOG_FILE', '/var/log/reverie/django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'translator': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# =============================================================================
# Cache Configuration (Redis for production)
# =============================================================================

if os.getenv('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.getenv('REDIS_URL'),
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# =============================================================================
# API Rate Limiting
# =============================================================================

# Rate limit settings (requests per minute per IP)
API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', '60'))

# =============================================================================
# Simulation Storage Configuration
# =============================================================================

# Storage paths - can be overridden for cloud storage
SIMULATION_STORAGE_PATH = os.getenv('SIMULATION_STORAGE_PATH', os.path.join(BASE_DIR, 'storage'))
TEMP_STORAGE_PATH = os.getenv('TEMP_STORAGE_PATH', os.path.join(BASE_DIR, 'temp_storage'))
COMPRESSED_STORAGE_PATH = os.getenv('COMPRESSED_STORAGE_PATH', os.path.join(BASE_DIR, 'compressed_storage'))

# =============================================================================
# External Agent API Configuration
# =============================================================================

# API authentication
REQUIRE_API_AUTH = os.getenv('REQUIRE_API_AUTH', 'True').lower() in {'true', '1', 'yes'}
API_KEYS = [key.strip() for key in os.getenv('API_KEYS', '').split(',') if key.strip()]

# WebSocket configuration (for real-time event streaming)
WEBSOCKET_HOST = os.getenv('WEBSOCKET_HOST', '0.0.0.0')
WEBSOCKET_PORT = int(os.getenv('WEBSOCKET_PORT', '8001'))
