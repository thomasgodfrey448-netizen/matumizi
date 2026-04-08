#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from expenses.models import ExpenseRequest
from retirement.models import RetirementForm
from core.models import Department, Treasurer

# Create test users and data
try:
    admin_user = User.objects.create_user(username='test_admin', password='test123', is_staff=True, is_superuser=True)
except:
    admin_user = User.objects.get(username='test_admin')

try:
    dept = Department.objects.create(name='Test Dept Dashboard', is_active=True)
except:
    dept = Department.objects.get(name='Test Dept Dashboard')

# Create expenses with different payment statuses
try:
    paid_expense = ExpenseRequest.objects.create(
        submitted_by=admin_user,
        first_name='John', last_name='Paid',
        phone_number='1234567890',
        department=dept,
        date='2026-04-06',
        reason='Test',
        total_amount=1000.00,
        status='approved',
        is_paid=True
    )
except:
    pass

try:
    unpaid_expense = ExpenseRequest.objects.create(
        submitted_by=admin_user,
        first_name='Jane', last_name='Unpaid',
        phone_number='1234567890',
        department=dept,
        date='2026-04-06',
        reason='Test',
        total_amount=2000.00,
        status='approved',
        is_paid=False
    )
except:
    pass

# Test
client = Client()
client.login(username='test_admin', password='test123')

print("Testing Expenses Dashboard")
print("-" * 50)
response = client.get('/expenses/')
if response.status_code == 200:
    content = response.content.decode('utf-8')
    checks = {
        'Payment column header': '<th>Payment</th>' in content,
        'Paid badge': 'badge-approved\">Paid</span>' in content,
        'Unpaid badge': 'badge-rejected\">Unpaid</span>' in content,
    }
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")
else:
    print(f"  ✗ Failed (Status: {response.status_code})")

print("\nTesting Retirement Dashboard")
print("-" * 50)
response = client.get('/retirement/')
if response.status_code == 200:
    content = response.content.decode('utf-8')
    checks = {
        'Payment column header': '<th>Payment</th>' in content,
    }
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")
else:
    print(f"  ✗ Failed (Status: {response.status_code})")

# Test retirement detail - should NOT have payment section
print("\nTesting Retirement Detail (No Payment Section)")
print("-" * 50)
retirement = RetirementForm.objects.filter(status='approved', is_paid=False).first()
if retirement:
    response = client.get(f'/retirement/{retirement.pk}/')
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        checks = {
            'Payment Status section removed': 'PAYMENT STATUS SECTION' not in content,
            'Mark as Paid button removed': 'update_payment' not in content,
            'Payment Date field removed': 'payment_date' not in content,
        }
        for check, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check}")
    else:
        print(f"  ✗ Failed (Status: {response.status_code})")
else:
    print("  No approved unpaid retirement forms found")

# Test expense detail - should still have payment section
print("\nTesting Expense Detail (Payment Section Still There)")
print("-" * 50)
expense = ExpenseRequest.objects.filter(status='approved', is_paid=False).first()
if expense:
    response = client.get(f'/expenses/{expense.pk}/')
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        checks = {
            'Payment Status section present': 'Payment Status' in content,
            'Mark as Paid button present': 'Mark as Paid' in content,
        }
        for check, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check}")
    else:
        print(f"  ✗ Failed (Status: {response.status_code})")
else:
    print("  No approved unpaid expenses found")

print("\n" + "="*50)
print("All Tests Completed!")
