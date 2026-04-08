import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()
from django.test import Client
import traceback

c = Client()

# Test home page
try:
    r = c.get('/')
    print(f'Home: {r.status_code}')
except Exception as e:
    print(f'Home Error: {e}')
    traceback.print_exc()

# Test login page
try:
    r = c.get('/login/')
    print(f'Login: {r.status_code}')
except Exception as e:
    print(f'Login Error: {e}')

# Test treasurer dashboard (requires login)
try:
    r = c.get('/treasurer-dashboard/')
    print(f'Treasurer Dashboard: {r.status_code}')
    if r.status_code == 500:
        print("500 ERROR ON TREASURER DASHBOARD!")
        if hasattr(r, 'exc_info'):
            print(f"Exception: {r.exc_info}")
except Exception as e:
    print(f'Treasurer Dashboard Error: {e}')
    traceback.print_exc()

# Test expense dashboard
try:
    r = c.get('/expenses/dashboard/')
    print(f'Expense Dashboard: {r.status_code}')
except Exception as e:
    print(f'Expense Dashboard Error: {e}')

# Test retirement dashboard  
try:
    r = c.get('/retirement/dashboard/')
    print(f'Retirement Dashboard: {r.status_code}')
except Exception as e:
    print(f'Retirement Dashboard Error: {e}')
