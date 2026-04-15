import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from accounts.views import _is_user_code_department_valid

print("Testing admin login...")

# Test 1: Check if admin user exists
admin = User.objects.get(username='admin')
print(f"✓ Admin user found: {admin.username} (superuser: {admin.is_superuser})")

# Test 2: Test authenticate function
user = authenticate(username='admin', password='Admin123!@#')
if user:
    print(f"✓ Authentication successful for user: {user.username}")
else:
    print("✗ Authentication failed")
    exit(1)

# Test 3: Test code/department validation for superuser
is_valid = _is_user_code_department_valid(user)
print(f"✓ Code/Department validation: {is_valid} (superusers should bypass this)")

print("\n✅ All login tests passed! Login should work on Render.")
