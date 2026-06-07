"""
Local development Django settings for frontend_server.

This file extends the base settings with local development overrides.
It is imported by __init__.py after base.py, so all base settings are
already available. Only override the settings needed for local development.

Import order (in __init__.py):
1. from .base import *     <- All base settings loaded
2. from .local import *    <- This file overrides specific settings
"""

# Local development overrides
DEBUG = True

# Allow local development hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# CORS settings for local development - allow all origins
CORS_ORIGIN_ALLOW_ALL = True

# Disable API authentication in development for easier testing
REQUIRE_API_AUTH = False





