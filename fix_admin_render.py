#!/usr/bin/env python
"""
Direct script to create or fix admin superuser.
Run: python fix_admin_render.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'matoleo_system'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import connection

# Render deployment credentials (hardcoded override)
# IMPORTANT: These must match render.yaml envVars
username = 'thomas'
password = 'Hot@2000'
email = 'thomasgodfrey448@gmail.com'

# If Render env vars are set, they take precedence for flexibility
if os.environ.get('ADMIN_USERNAME'):
    username = os.environ.get('ADMIN_USERNAME').lower().strip()
if os.environ.get('ADMIN_PASSWORD'):
    password = os.environ.get('ADMIN_PASSWORD').strip()
if os.environ.get('ADMIN_EMAIL'):
    email = os.environ.get('ADMIN_EMAIL').strip()

print(f"🔧 Fixing admin user on Render database...")
print(f"  User: {username}")
print(f"  Email: {email}")

try:
    # Test database connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("✓ Database connection successful")
except Exception as e:
    print(f"✗ Database error: {e}")
    sys.exit(1)

try:
    # Try to get existing user
    user = User.objects.get(username=username)
    # Update password and email
    user.set_password(password)
    user.email = email
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"✓ Updated existing superuser: {username}")
except User.DoesNotExist:
    # Create new superuser
    user = User.objects.create_superuser(username, email, password)
    print(f"✓ Created new superuser: {username}")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Verify
print(f"\n✓ Admin credentials:")
print(f"  Username: {username}")
print(f"  Password: {password}")
print(f"  Email: {email}")
print(f"\n✓ Ready to login at: https://matoleo-system.onrender.com/admin/")
