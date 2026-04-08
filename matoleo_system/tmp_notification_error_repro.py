import os
import sys
root = os.path.abspath('.')
sys.path.insert(0, root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from django.test import Client
from core.models import Notification

errors = []
for notif in Notification.objects.all()[:5]:
    client = Client()
    client.force_login(notif.recipient)
    path = f"/notifications/{notif.pk}/read/"
    response = client.get(path, follow=True)
    if response.status_code >= 400:
        errors.append((notif.pk, notif.link, response.status_code, response.redirect_chain, response.content[:800]))
    elif response.redirect_chain and response.redirect_chain[-1][1] >= 400:
        errors.append((notif.pk, notif.link, response.redirect_chain[-1][1], response.redirect_chain, response.content[:800]))

print('checked', Notification.objects.count(), 'notifications')
print('errors', len(errors))
for item in errors[:50]:
    print(item)

with open('tmp_notification_test_result.txt', 'w') as f:
    f.write(f'checked {Notification.objects.count()} notifications\n')
    f.write(f'errors {len(errors)}\n')
    for item in errors[:10]:
        f.write(str(item) + '\n')
