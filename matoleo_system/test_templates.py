#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.template.loader import render_to_string

# Test template loads
print("Testing template loading...")
try:
    # Check if Payment column exists in template source
    with open('templates/expenses/dashboard.html', 'r') as f:
        content = f.read()
    if '<th>Payment</th>' in content:
        print("✓ Expenses dashboard has Payment column")
    else:
        print("✗ Expenses dashboard missing Payment column")
except Exception as e:
    print(f"✗ Error checking expenses dashboard: {str(e)[:100]}")

try:
    # Check if Payment column exists in template source
    with open('templates/retirement/dashboard.html', 'r') as f:
        content = f.read()
    if '<th>Payment</th>' in content:
        print("✓ Retirement dashboard has Payment column")
    else:
        print("✗ Retirement dashboard missing Payment column")
except Exception as e:
    print(f"✗ Error checking retirement dashboard: {str(e)[:100]}")

try:
    content = render_to_string('retirement/detail.html', {'form': object(), 'user': object(), 'is_admin': True})
    if 'PAYMENT STATUS SECTION' in content:
        print("✗ Retirement detail has payment section (should be removed)")
    else:
        print("✓ Retirement detail payment section removed")
except Exception as e:
    print(f"✗ Error loading retirement detail: {str(e)[:100]}")

print("\nDone!")
