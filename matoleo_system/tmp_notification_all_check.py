import os
import sys
root = os.path.abspath('matoleo_system')
sys.path.insert(0, root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from django.test import Client
from core.models import Notification
errors = []
for notif in Notification.objects.all():
    client = Client()
    client.force_login(notif.recipient)
    path = f"/notifications/{notif.pk}/read/"
    response = client.get(path)
    if response.status_code >= 400:
        errors.append((notif.pk, notif.link, response.status_code, response.content[:300]))
    elif response.redirect_chain:
        location = response.redirect_chain[-1][0]
        if response.redirect_chain[-1][1] >= 400:
            errors.append((notif.pk, notif.link, response.redirect_chain[-1][1], location))
print('checked', Notification.objects.count(), 'notifications')
print('errors', len(errors))
for item in errors[:50]:
    print(item)
