#!/usr/bin/env python
"""
Test script to verify expense form submission works without internal server errors.
"""
import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from core.models import Department, UserProfile
from expenses.models import ExpenseRequest, Budget

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

def test_expense_form_submission():
    """Test that expense form can be submitted without errors."""
    print("Testing expense form submission...")

    # Create test client
    client = Client()

    # Create test department
    dept, created = Department.objects.get_or_create(
        name='Test Department',
        defaults={'is_active': True}
    )

    # Create test budget for the department
    budget, created = Budget.objects.get_or_create(
        department=dept,
        defaults={'total_budget': 10000.00}
    )

    # Create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()

    # Create user profile
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'department': dept,
            'is_approved': True
        }
    )

    # Login the user
    login_success = client.login(username='testuser', password='testpass123')
    if not login_success:
        print("❌ Login failed")
        return False

    print("✓ User logged in successfully")

    # Test GET request to form
    response = client.get('/expenses/create/')
    if response.status_code != 200:
        print(f"❌ GET /expenses/create/ failed with status {response.status_code}")
        return False

    print("✓ Form page loads successfully")

    # Test POST request with form data
    form_data = {
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '+1234567890',
        'department': dept.id,
        'date': date.today().isoformat(),
        'reason': 'Test expense for budget validation',
        'budget_choice': 'department',  # Use department budget
        'items-TOTAL_FORMS': '1',
        'items-INITIAL_FORMS': '0',
        'items-MIN_NUM_FORMS': '0',
        'items-MAX_NUM_FORMS': '1000',
        'items-0-description': 'Test item',
        'items-0-quantity': '1',
        'items-0-unit_price': '100.00',
        'items-0-total': '100.00',
    }

    # First save as draft
    response = client.post('/expenses/create/', form_data)
    if response.status_code not in [200, 302]:
        print(f"❌ POST /expenses/create/ failed with status {response.status_code}")
        print(f"Response content: {response.content.decode()[:500]}")
        return False

    print("✓ Form submission (draft) successful")

    # Check if expense was created
    expenses = ExpenseRequest.objects.filter(submitted_by=user)
    if not expenses.exists():
        print("❌ Expense was not created")
        return False

    expense = expenses.last()
    print(f"✓ Expense created with ID {expense.id}")

    # Test submitting the draft
    response = client.post(f'/expenses/submit/{expense.id}/')
    if response.status_code not in [200, 302]:
        print(f"❌ POST /expenses/submit/{expense.id}/ failed with status {response.status_code}")
        return False

    print("✓ Expense submission successful")

    # Clean up
    expense.delete()
    if created:
        user.delete()
    if budget_created:
        budget.delete()
    if dept_created:
        dept.delete()

    print("✅ All tests passed! Expense form submission works correctly.")
    return True

if __name__ == '__main__':
    try:
        success = test_expense_form_submission()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)