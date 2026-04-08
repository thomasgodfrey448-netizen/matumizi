import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'matoleo_system')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from core.models import Notification
User = get_user_model()
print('Users:', User.objects.count())
print('Notifications:', Notification.objects.count())
print(list(Notification.objects.values('pk','recipient_id','link')[:20]))
