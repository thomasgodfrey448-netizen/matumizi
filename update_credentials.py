import os
import sys
import django

sys.path.insert(0, 'matoleo_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.contrib.auth.models import User

# Update the superuser to match Render credentials
u = User.objects.get(username='thomas')
u.set_password('Hot@2000')
u.save()
print('✓ Updated superuser thomas password to: Hot@2000')
print('✓ Local credentials now match Render config:')
print('  Username: thomas')
print('  Password: Hot@2000')
