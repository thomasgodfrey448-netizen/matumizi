import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()
from django.test import Client
from django.contrib.auth.models import User
from core.models import Department, UserProfile
from expenses.models import Budget

client = Client()
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User'}
)
if created:
    user.set_password('testpass123')
    user.save()

department, _ = Department.objects.get_or_create(name='Test Department', defaults={'is_active': True})
profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'department': department, 'is_approved': True})
budget, _ = Budget.objects.get_or_create(department=department, defaults={'church_budget': 1000.00, 'contribution1_name': 'Contrib 1', 'contribution1_amount': 500.00, 'contribution2_name': 'Contrib 2', 'contribution2_amount': 300.00})
if not _:
    budget.church_budget = 1000.00
    budget.contribution1_name = 'Contrib 1'
    budget.contribution1_amount = 500.00
    budget.contribution2_name = 'Contrib 2'
    budget.contribution2_amount = 300.00
    budget.save()

login_success = client.login(username='testuser', password='testpass123')
print('login', login_success)

for choice in ['church_budget', 'contribution1', 'contribution2', 'mk']:
    print('\n--- testing budget_choice:', choice)
    data = {
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '+1234567890',
        'department': str(department.id),
        'date': date.today().isoformat(),
        'reason': 'Test expense',
        'budget_choice': choice,
        'item_description[]': ['Item1'],
        'item_amount[]': ['100'],
    }
    response = client.post('/expenses/new/', data, HTTP_HOST='127.0.0.1')
    print('status', response.status_code)
    print('location', response['Location'] if response.status_code in (301,302) else '')
    print('has_context', hasattr(response, 'context'))
    if response.status_code == 200 and hasattr(response, 'context') and response.context is not None:
        print('context_len', len(response.context))
        ctx = response.context[0]
        print('context_keys', list(ctx.keys()))
        if 'action' in ctx:
            print('action', ctx['action'])
        if 'budget_options' in ctx:
            print('budget_options', [opt['value'] for opt in ctx['budget_options']])
        if 'messages' in ctx:
            print('messages', [str(m) for m in ctx['messages']])
    print(response.content.decode()[:1200])
    if response.status_code in (301,302):
        response2 = client.get(response['Location'], HTTP_HOST='127.0.0.1')
        print('detail status', response2.status_code)
        print(response2.content.decode()[:1200])
