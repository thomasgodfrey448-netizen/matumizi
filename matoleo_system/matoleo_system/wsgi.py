"""
WSGI config for matoleo_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')

# Ensure static files are collected on startup in deployed environments.
# This is a safe fallback when the Render build/release commands do not run collectstatic.
try:
    call_command('collectstatic', verbosity=0, interactive=False)
except Exception:
    pass

application = get_wsgi_application()
