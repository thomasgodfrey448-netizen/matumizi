import os
import sys
root = os.path.abspath('matoleo_system')
sys.path.insert(0, root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from core.models import Notification
bad = []
for n in Notification.objects.all():
    link = n.link
    if not link:
        continue
    if ' ' in link:
        bad.append((n.pk, link, 'contains space'))
    if link.startswith('http://') or link.startswith('https://'):
        bad.append((n.pk, link, 'external'))
    if not link.startswith('/'):
        bad.append((n.pk, link, 'not starting slash'))
print('bad count', len(bad))
for item in bad[:50]:
    print(item)
