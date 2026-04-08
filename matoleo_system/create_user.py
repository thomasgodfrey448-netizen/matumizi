import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.contrib.auth.models import User

# Delete existing superuser if any
User.objects.filter(is_superuser=True).delete()

# Create new superuser
User.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='admin123'
)

print("✅ New superuser created!")
print("Username: admin")
print("Password: admin123")
