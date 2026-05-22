#!/usr/bin/env python
"""
HTTP test to reproduce the budget selection 500 error
"""
import requests
from datetime import date
import json

BASE_URL = 'http://127.0.0.1:8000'

# Create a session to handle cookies/CSRF
session = requests.Session()

# Step 1: GET the form page
print("Step 1: Getting form page...")
response = session.get(f'{BASE_URL}/accounts/login/')
print(f"  Status: {response.status_code}")

# Step 2: Login
print("\nStep 2: Logging in...")
login_data = {
    'username': 'budgettest',
    'password': 'testpass'
}
response = session.post(f'{BASE_URL}/accounts/login/', data=login_data, follow_redirects=True)
print(f"  Status: {response.status_code}")

# Step 3: Get the expense form
print("\nStep 3: Getting expense form...")
response = session.get(f'{BASE_URL}/expenses/new/')
print(f"  Status: {response.status_code}")
if response.status_code == 200:
    # Extract CSRF token
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    if csrf_token:
        csrf_token = csrf_token['value']
        print(f"  CSRF Token found: {csrf_token[:20]}...")
    else:
        print("  No CSRF token found!")
        csrf_token = None

# Step 4: Submit form with budget selection
print("\nStep 4: Testing budget selection...")
for budget_choice in ['church_budget', 'contribution1', 'contribution2', 'mk']:
    print(f"\n  Testing budget_choice='{budget_choice}'...")
    
    form_data = {
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '+255000000000',
        'department': '1',  # Adjust based on actual dept ID
        'date': date.today().isoformat(),
        'reason': f'Test for {budget_choice}',
        'budget_choice': budget_choice,
        'item_description[]': ['Test item'],
        'item_amount[]': ['100.00'],
    }
    
    if csrf_token:
        form_data['csrfmiddlewaretoken'] = csrf_token
    
    try:
        response = session.post(f'{BASE_URL}/expenses/new/', data=form_data, follow_redirects=False)
        print(f"    Response Status: {response.status_code}")
        
        if response.status_code == 500:
            print(f"    ✗ ERROR 500!")
            print(f"    Response text (first 500 chars): {response.text[:500]}")
        elif response.status_code == 302:
            print(f"    ✓ Redirect to detail page {response.headers.get('Location')}")
        elif response.status_code == 200:
            print(f"    Form re-rendered (validation error)")
            if 'messages' in response.text:
                print(f"    May contain error messages")
    except Exception as e:
        print(f"    Exception: {type(e).__name__}: {e}")

print("\nDone")
