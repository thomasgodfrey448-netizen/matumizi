"""
WSGI config for matoleo_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

# Run migrations and create admin user on startup
try:
    from django.core.management import call_command
    from django.contrib.auth.models import User

    # Run migrations
    call_command('migrate', verbosity=1, interactive=False)

    # Create admin user
    admin_username = os.environ.get('USERNAME') or os.environ.get('username') or 'admin'
    admin_password = os.environ.get('PASSWORD') or os.environ.get('password') or 'Admin123!@#'
    admin_email = os.environ.get('EMAIL') or os.environ.get('email') or 'admin@example.com'

    if not User.objects.filter(username=admin_username).exists():
        User.objects.create_superuser(admin_username, admin_email, admin_password)
        print(f"✓ Created admin user: {admin_username}")
    else:
        user = User.objects.get(username=admin_username)
        user.set_password(admin_password)
        user.email = admin_email
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print(f"✓ Updated admin user: {admin_username}")

except Exception as e:
    print(f"Warning: Could not run startup tasks: {e}")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
