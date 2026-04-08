#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.template.loader import render_to_string
from django.contrib.auth.models import User
from core.models import Announcement

# Try to render the treasurer dashboard template
try:
    context = {
        'pending_payments_expenses': [],
        'pending_payments_retirement': [],
        'recent_payments_expenses': [],
        'recent_payments_retirement': [],
        'announcements': [],
    }
    
    html = render_to_string('core/treasurer_dashboard.html', context)
    print("✓ Treasurer dashboard template rendered successfully!")
    print(f"Template output length: {len(html)} characters")
    
except Exception as e:
    print(f"✗ Error rendering template: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    import traceback
    traceback.print_exc()
