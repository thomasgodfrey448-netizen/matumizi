#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'matoleo_system'))

django.setup()

from django.contrib.auth.models import User

username = 'admin'
email = 'admin@church.local'
password = 'Admin@12345'

try:
    user = User.objects.create_superuser(username, email, password)
    print(f"✓ Admin user created successfully")
    print(f"Username: {username}")
    print(f"Password: {password}")
except Exception as e:
    print(f"Note: {str(e)}")
    print(f"Admin credentials if created:")
    print(f"Username: {username}")
    print(f"Password: {password}")
