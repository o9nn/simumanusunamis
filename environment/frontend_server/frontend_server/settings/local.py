"""
Local development Django settings for frontend_server.

This file extends the base settings with local development overrides.
Import this file only when running locally (not imported in production).
"""
import os

# Local development overrides
DEBUG = True

# Allow local development hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# CORS settings for local development
CORS_ORIGIN_ALLOW_ALL = True

# Disable API authentication in development for easier testing
REQUIRE_API_AUTH = False
API_KEYS = []









