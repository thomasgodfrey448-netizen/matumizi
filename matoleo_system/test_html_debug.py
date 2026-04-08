#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.template.loader import render_to_string

# Test template loads
print("Testing expense dashboard...")
try:
    content = render_to_string('expenses/dashboard.html', {'requests': [], 'user': None})
    # Print first few lines of thead
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '<thead>' in line:
            print("Found thead at line", i)
            for j in range(i, min(i+20, len(lines))):
                print(lines[j])
            break
except Exception as e:
    print(f"Error: {e}")
