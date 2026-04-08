import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'matoleo_system')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from django.test import Client
from core.models import Notification
User = get_user_model()
try:
    notif = Notification.objects.first()
    print('Notification:', notif.pk, notif.recipient_id, notif.link, notif.is_read)
    user = notif.recipient
    client = Client()
    client.force_login(user)
    path = f"/notifications/{notif.pk}/read/"
    print('GET', path)
    response = client.get(path)
    print('status', response.status_code)
    if hasattr(response, 'redirect_chain'):
        print('redirect_chain', response.redirect_chain)
    print('content snippet:', response.content[:500])
except Exception as e:
    import traceback
    traceback.print_exc()
