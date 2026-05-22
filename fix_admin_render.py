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

# Render deployment credentials (hardcoded override for consistency)
# IMPORTANT: Use Render env vars if explicitly set, otherwise use defaults
# Do NOT use system environment variables as fallback (e.g., USERNAME, PASSWORD)
username = os.environ.get('ADMIN_USERNAME', '').strip() or 'Thomas'
password = os.environ.get('ADMIN_PASSWORD', '').strip() or 'Hot@2000'
email = os.environ.get('ADMIN_EMAIL', '').strip() or 'thomasgodfrey448@gmail.com'

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

# Ensure UserProfile exists for the superuser
try:
    from core.models import UserProfile, Department
    profile, created = UserProfile.objects.get_or_create(user=user)
    if created:
        print(f"✓ Created UserProfile for {username}")
        # Assign to a default department if needed
        try:
            default_dept = Department.objects.filter(is_active=True).first()
            if default_dept:
                profile.department = default_dept
                profile.save()
                print(f"✓ Assigned default department to {username}")
        except Exception as dept_err:
            print(f"  (Note: Could not assign department: {dept_err})")
    else:
        print(f"✓ UserProfile exists for {username}")
except Exception as profile_err:
    print(f"  (Warning: Could not verify/create UserProfile: {profile_err})")

# Verify
print(f"\n✓ Admin credentials:")
print(f"  Username: {username}")
print(f"  Password: {password}")
print(f"  Email: {email}")
print(f"\n✓ Ready to login at: https://matoleo-system.onrender.com/admin/")
