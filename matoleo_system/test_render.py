import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
import django
django.setup()

from django.template.loader import render_to_string
from expenses.models import ExpenseRequest
from retirement.models import RetirementForm
from core.models import Announcement

# Try rendering treasurer dashboard
try:
    pending_payments_expenses = ExpenseRequest.objects.filter(status='approved', is_paid=False).order_by('-submitted_at')
    pending_payments_retirement = RetirementForm.objects.filter(status='approved', is_paid=False).order_by('-submitted_at')
    recent_payments_expenses = ExpenseRequest.objects.filter(is_paid=True).order_by('-paid_at')[:10]
    recent_payments_retirement = RetirementForm.objects.filter(is_paid=True).order_by('-paid_at')[:10]
    announcements = Announcement.objects.all().order_by('-created_at')[:5]
    
    context = {
        'pending_payments_expenses': pending_payments_expenses,
        'pending_payments_retirement': pending_payments_retirement,
        'recent_payments_expenses': recent_payments_expenses,
        'recent_payments_retirement': recent_payments_retirement,
        'announcements': announcements,
        'unread_notifications_count': 0,
    }
    
    html = render_to_string('core/treasurer_dashboard.html', context)
    print("✓ Treasurer dashboard rendered successfully")
    
except Exception as e:
    print(f"✗ Treasurer dashboard error: {e}")
    import traceback
    traceback.print_exc()

# Try rendering expense detail
try:
    expense = ExpenseRequest.objects.first()
    if expense:
        context = {
            'expense': expense,
            'is_approver': False,
            'is_admin': False,
            'is_treasurer': False,
            'can_first_approve': False,
            'can_second_approve': False,
            'can_admin_approve': False,
            'can_mark_paid': False,
        }
        html = render_to_string('expenses/detail.html', context)
        print("✓ Expense detail rendered successfully")
    else:
        print("No expense found to test")
except Exception as e:
    print(f"✗ Expense detail error: {e}")
    import traceback
    traceback.print_exc()

# Try rendering retirement detail
try:
    retirement = RetirementForm.objects.first()
    if retirement:
        context = {
            'form': retirement,
            'is_approver': False,
            'is_admin': False,
            'is_treasurer': False,
            'can_first_approve': False,
            'can_second_approve': False,
            'can_admin_approve': False,
            'can_mark_paid': False,
        }
        html = render_to_string('retirement/detail.html', context)
        print("✓ Retirement detail rendered successfully")
    else:
        print("No retirement found to test")
except Exception as e:
    print(f"✗ Retirement detail error: {e}")
    import traceback
    traceback.print_exc()
