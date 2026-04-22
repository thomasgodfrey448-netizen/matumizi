#!/usr/bin/env python
"""
Debug script to reproduce the Budget Selection 500 Error
"""
import os
import sys
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from core.models import Department, UserProfile
from expenses.models import Budget, ExpenseRequest

# Clean up test data
User.objects.filter(username='budgettest').delete()
Department.objects.filter(name='Budget Test Dept').delete()

# Create test department and budget
dept = Department.objects.create(name='Budget Test Dept', is_active=True)
budget = Budget.objects.create(
    department=dept,
    church_budget=10000.00,
    contribution1_name='Fund A',
    contribution1_amount=3000.00,
    contribution2_name='Fund B',
    contribution2_amount=2000.00,
)

# Create test user
user = User.objects.create_user(username='budgettest', password='testpass')
profile, _ = UserProfile.objects.get_or_create(user=user)
profile.department = dept
profile.save()

# Initialize client
client = Client()
client.login(username='budgettest', password='testpass')

print("=" * 80)
print("DEBUG: Budget Selection 500 Error Reproduction")
print("=" * 80)

# Test form display (GET)
print("\n1. Testing form display (GET /expenses/new/)...")
response = client.get('/expenses/new/')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    print("   ✓ Form page loads successfully")
    if 'budget_options' in response.context:
        print(f"   Budget options in context: {response.context['budget_options']}")
else:
    print(f"   ✗ Error: {response.status_code}")

# Test each budget option with POST
budget_options = ['church_budget', 'contribution1', 'contribution2', 'mk']

for i, budget_choice in enumerate(budget_options):
    print(f"\n{i+2}. Testing POST with budget_choice='{budget_choice}'...")
    
    post_data = {
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '+255000000000',
        'department': str(dept.id),
        'date': date.today().isoformat(),
        'reason': f'Test reason for {budget_choice}',
        'budget_choice': budget_choice,
        'item_description[]': ['Test item'],
        'item_amount[]': ['100.00'],
    }
    
    try:
        response = client.post('/expenses/new/', post_data, follow=False)
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 302:
            print(f"   ✓ Success - redirected to detail page")
            # Check if expense was created
            expenses = ExpenseRequest.objects.filter(budget_choice=budget_choice).order_by('-created_at')
            if expenses.exists():
                print(f"   ✓ Expense created with budget_choice={budget_choice}")
            else:
                print(f"   ✗ Expense not found with budget_choice={budget_choice}")
        elif response.status_code == 500:
            print(f"   ✗ Server Error 500!")
            if hasattr(response, 'content'):
                print(f"   Error content snippet: {response.content[:500]}")
        else:
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                # Re-render case - validation error
                if 'messages' in response.context:
                    messages = list(response.context['messages'])
                    for msg in messages:
                        print(f"   Message: {msg}")
    except Exception as e:
        print(f"   ✗ Exception: {type(e).__name__}: {e}")

print("\n" + "=" * 80)
print("DEBUG: Checking stored expense records...")
print("=" * 80)

for budget_choice in budget_options:
    count = ExpenseRequest.objects.filter(budget_choice=budget_choice).count()
    print(f"Expenses with budget_choice='{budget_choice}': {count}")

print("\n✓ Debug script completed")
