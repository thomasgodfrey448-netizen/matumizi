#!/usr/bin/env python
"""
Test script to see actual HTTP responses from the server
"""
import os
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from core.models import Department, UserProfile
from expenses.models import Budget, ExpenseRequest

# Clean data
User.objects.filter(username='quicktest').delete()
Department.objects.filter(name='Quick Test Dept').delete()

# Create department and budget
dept = Department.objects.create(name='Quick Test Dept', is_active=True)
budget = Budget.objects.create(
    department=dept,
    church_budget=10000.00,
    contribution1_name='Fund A',
    contribution1_amount=3000.00,
    contribution2_name='Fund B',
    contribution2_amount=2000.00,
)

# Create user
user = User.objects.create_user(username='quicktest', password='quickpass')
profile, _ = UserProfile.objects.get_or_create(user=user)
profile.department = dept
profile.is_approved = True
profile.save()

# Use Django test client
client = Client()

# Try to login and get form
print("=" * 80)
print("TESTING: Form Submission with Budget Selection")
print("=" * 80)

print("\n1. Logging in...")
login_ok = client.login(username='quicktest', password='quickpass')
print(f"   Login status: {'OK' if login_ok else 'FAILED'}")

print("\n2. Getting form page...")
response = client.get('/expenses/new/', follow=False)
print(f"   Status: {response.status_code}")
if response.status_code != 200:
    print(f"   Error in form display!")
    print(f"   Content: {response.content[:300]}")

print("\n3. Submitting form with each budget...")
for budget_choice in ['church_budget', 'contribution1', 'contribution2', 'mk']:
    print(f"\n   Testing: {budget_choice}")
    response = client.post(f'/expenses/new/', {
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '+255000000000',
        'department': str(dept.id),
        'date': date.today().isoformat(),
        'reason': f'Test {budget_choice}',
        'budget_choice': budget_choice,
        'item_description[]': ['Test'],
        'item_amount[]': ['100'],
    }, follow=False)
    
    print(f"   Response Status: {response.status_code}")
    if response.status_code == 500:
        print(f"   ✗ 500 ERROR!")
        print(f"   Content snippet:\n{response.content.decode('utf-8', errors='ignore')[:800]}")
    elif response.status_code == 302:
        location = response.get('Location', '')
        print(f"   ✓ 302 Redirect to: {location}")
        # Try to view the redirect target
        detail_response = client.get(location, follow=False)
        print(f"   Detail page status: {detail_response.status_code}")
        if detail_response.status_code == 500:
            print(f"   ✗ Detail page has 500 ERROR!")
            print(f"   Content snippet: {detail_response.content.decode('utf-8', errors='ignore')[:800]}")
    else:
        print(f"   Unexpected status: {response.status_code}")

print("\n" + "=" * 80)
print("Test completed")
