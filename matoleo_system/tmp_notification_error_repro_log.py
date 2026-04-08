import os
import sys
root = os.path.abspath('matoleo_system')
sys.path.insert(0, root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from django.test import Client
from core.models import Notification

log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'tmp_notification_error_repro_log.txt'))
with open(log_path, 'w', encoding='utf-8') as f:
    f.write('starting\n')
    errors = []
    count = 0
    for notif in Notification.objects.all():
        count += 1
        f.write(f'notif {notif.pk} link={notif.link!r} recipient={notif.recipient_id}\n')
        client = Client()
        client.force_login(notif.recipient)
        path = f"/notifications/{notif.pk}/read/"
        response = client.get(path, follow=True)
        f.write(f' status={response.status_code} redirects={response.redirect_chain}\n')
        if response.status_code >= 400:
            errors.append((notif.pk, notif.link, response.status_code, response.redirect_chain, response.content[:800]))
        elif response.redirect_chain and response.redirect_chain[-1][1] >= 400:
            errors.append((notif.pk, notif.link, response.redirect_chain[-1][1], response.redirect_chain, response.content[:800]))
    f.write(f'checked {count} notifications\n')
    f.write(f'errors {len(errors)}\n')
    for item in errors[:50]:
        f.write(str(item) + '\n')
