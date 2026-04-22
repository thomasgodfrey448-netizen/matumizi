import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth.models import User
from core.models import Department, UserProfile
from expenses.models import Budget
from django.contrib.messages import get_messages
from datetime import date

client = Client(HTTP_HOST='localhost')
user, created = User.objects.get_or_create(username='inspectuser', defaults={'email':'inspect@example.com','first_name':'Inspect','last_name':'User'})
if created:
    user.set_password('inspectpass123')
    user.save()

profile, created = UserProfile.objects.get_or_create(user=user)
if not profile.department:
    profile.department = Department.objects.create(name='Inspect Budget Dept', is_active=True)
    profile.is_approved = True
    profile.save()

budget, created = Budget.objects.get_or_create(
    department=profile.department,
    defaults={
        'church_budget': 10000.00,
        'contribution1_name': 'Fund A',
        'contribution1_amount': 3000.00,
        'contribution2_name': 'Fund B',
        'contribution2_amount': 2000.00,
    }
)
client.login(username='inspectuser', password='inspectpass123')

for choice in ['church_budget', 'contribution1', 'contribution2', 'mk']:
    print('===', choice)
    data = {
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '+255000000000',
        'department': str(profile.department.id),
        'date': date.today().isoformat(),
        'reason': 'Test',
        'budget_choice': choice,
        'item_description[]': ['Test item'],
        'item_amount[]': ['100'],
    }
    resp = client.post('/expenses/new/', data, HTTP_HOST='localhost')
    print('status', resp.status_code)
    print('location', resp.get('Location'))
    if hasattr(resp, 'context') and resp.context is not None:
        print('context keys', list(resp.context.keys()))
    try:
        msgs = [str(m) for m in get_messages(resp.wsgi_request)]
        print('messages', msgs)
    except Exception as e:
        print('messages exception', e)
    txt = resp.content.decode('utf-8', errors='ignore')
    if 'Invalid budget choice' in txt:
        print('found invalid budget choice text')
    if 'Please fill all required fields' in txt:
        print('found missing required fields text')
    if 'Insufficient balance' in txt:
        print('found insufficient balance text')
    print('budget_choice input present', 'name="budget_choice"' in txt)
    print('---- snippet ----')
    print(txt[txt.find('<form'):txt.find('</form>')+7])
    print('===================\n')
