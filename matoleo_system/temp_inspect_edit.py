import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth.models import User
from core.models import Department, UserProfile
from expenses.models import Budget, ExpenseRequest
from datetime import date

client = Client(HTTP_HOST='localhost')
user, created = User.objects.get_or_create(username='inspectuser2', defaults={'email':'inspect2@example.com','first_name':'Inspect','last_name':'User'})
if created:
    user.set_password('inspectpass123')
    user.save()

profile, created = UserProfile.objects.get_or_create(user=user)
if not profile.department:
    profile.department = Department.objects.create(name='Inspect Budget Dept 2', is_active=True)
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
client.login(username='inspectuser2', password='inspectpass123')

for choice in ['church_budget', 'contribution1', 'contribution2', 'mk']:
    print('=== create', choice)
    data = {
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '+255000000001',
        'department': str(profile.department.id),
        'date': date.today().isoformat(),
        'reason': 'Test',
        'budget_choice': choice,
        'item_description[]': ['Test item'],
        'item_amount[]': ['100'],
    }
    resp = client.post('/expenses/new/', data, HTTP_HOST='localhost')
    print('create status', resp.status_code, 'location', resp.get('Location'))
    if resp.status_code == 302:
        location = resp['Location']
        pk = int(location.strip('/').split('/')[-1])
        print('created pk', pk)
        expense = ExpenseRequest.objects.get(pk=pk)
        print('budget_choice stored', expense.budget_choice)
        # test editing with same budget
        edit_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+255000000001',
            'department': str(profile.department.id),
            'date': date.today().isoformat(),
            'reason': 'Edited test',
            'budget_choice': choice,
            'item_description[]': ['Edited item'],
            'item_amount[]': ['200'],
        }
        resp2 = client.post(f'/expenses/{pk}/edit/', edit_data, HTTP_HOST='localhost')
        print('edit status', resp2.status_code, 'location', resp2.get('Location'))
    print('')
