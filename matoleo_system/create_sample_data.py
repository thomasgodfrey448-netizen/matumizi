import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Department, Approver, UserProfile, Announcement
from expenses.models import ExpenseRequest, ExpenseItem
from retirement.models import RetirementForm, RetirementItem

def create_sample_data():
    print("Creating sample data...")

    # Create departments
    dept_a, _ = Department.objects.get_or_create(name='Department A', defaults={'is_active': True})
    dept_b, _ = Department.objects.get_or_create(name='Department B', defaults={'is_active': True})

    # Create users
    admin_user = User.objects.filter(username='admin').first()
    if not admin_user:
        admin_user = User.objects.create_user(username='admin', password='admin123', is_staff=True, is_superuser=True)

    first_approver_user = User.objects.filter(username='first_approver').first()
    if not first_approver_user:
        first_approver_user = User.objects.create_user(username='first_approver', password='pass123')

    second_approver_user = User.objects.filter(username='second_approver').first()
    if not second_approver_user:
        second_approver_user = User.objects.create_user(username='second_approver', password='pass123')

    regular_user = User.objects.filter(username='regular').first()
    if not regular_user:
        regular_user = User.objects.create_user(username='regular', password='pass123')

    # Create approver profiles
    first_approver, _ = Approver.objects.get_or_create(
        user=first_approver_user,
        defaults={'level': 'first', 'is_active': True}
    )
    first_approver.departments.add(dept_a)

    second_approver, _ = Approver.objects.get_or_create(
        user=second_approver_user,
        defaults={'level': 'second', 'is_active': True}
    )

    # Create user profiles
    profile, _ = UserProfile.objects.get_or_create(user=regular_user)
    profile.department = dept_a
    profile.is_approved = True
    profile.save()

    # Create sample expense requests
    expense_a, _ = ExpenseRequest.objects.get_or_create(
        submitted_by=regular_user,
        department=dept_a,
        defaults={
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+1234567890',
            'date': date.today(),
            'reason': 'Test expense A',
            'total_amount': 100.00,
            'status': 'submitted'
        }
    )

    expense_b, _ = ExpenseRequest.objects.get_or_create(
        submitted_by=regular_user,
        department=dept_b,
        defaults={
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone_number': '+1234567890',
            'date': date.today(),
            'reason': 'Test expense B',
            'total_amount': 200.00,
            'status': 'submitted'
        }
    )

    # Add expense items
    ExpenseItem.objects.get_or_create(
        expense_request=expense_a,
        defaults={
            'description': 'Office supplies',
            'amount': 50.00,
            'order': 1
        }
    )
    ExpenseItem.objects.get_or_create(
        expense_request=expense_a,
        defaults={
            'description': 'Travel expenses',
            'amount': 50.00,
            'order': 2
        }
    )

    # Create sample retirement forms
    retirement_a, _ = RetirementForm.objects.get_or_create(
        submitted_by=regular_user,
        department=dept_a,
        defaults={
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+1234567890',
            'date_of_request': date.today(),
            'date_of_retirement': date.today(),
            'reason': 'Test retirement A',
            'remaining_amount': 500.00,
            'total_amount': 100.00,
            'status': 'submitted'
        }
    )

    retirement_b, _ = RetirementForm.objects.get_or_create(
        submitted_by=regular_user,
        department=dept_b,
        defaults={
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone_number': '+1234567890',
            'date_of_request': date.today(),
            'date_of_retirement': date.today(),
            'reason': 'Test retirement B',
            'remaining_amount': 300.00,
            'total_amount': 200.00,
            'status': 'submitted'
        }
    )

    # Add retirement items
    RetirementItem.objects.get_or_create(
        retirement_form=retirement_a,
        defaults={
            'description': 'Unused budget',
            'amount': 100.00
        }
    )

    # Create sample announcements
    Announcement.objects.get_or_create(
        title='Welcome to Matumizi System',
        defaults={
            'content': 'Welcome to the new financial management system for Makongo Juu SDA Church. This system helps manage expense requests and retirement forms efficiently.',
            'is_active': True,
            'created_by': admin_user
        }
    )

    Announcement.objects.get_or_create(
        title='System Maintenance Notice',
        defaults={
            'content': 'The system will undergo maintenance on Sunday evenings from 10 PM to 12 AM. Please plan your submissions accordingly.',
            'is_active': True,
            'created_by': admin_user
        }
    )

    Announcement.objects.get_or_create(
        title='New Approval Process',
        defaults={
            'content': 'We have implemented a two-level approval process for better financial control. All requests now require first and second level approvals.',
            'is_active': True,
            'created_by': admin_user
        }
    )

    Announcement.objects.get_or_create(
        title='Contact Information',
        defaults={
            'content': 'For any questions about the system, please contact the church treasurer or the system administrator.',
            'is_active': True,
            'created_by': admin_user
        }
    )

    print("Sample data created successfully!")
    print("Users created:")
    print("- admin (admin123) - Superuser")
    print("- first_approver (pass123) - First level approver")
    print("- second_approver (pass123) - Second level approver")
    print("- regular (pass123) - Regular user")
    print("Sample expense and retirement requests created.")
    print("Sample announcements created.")

if __name__ == '__main__':
    create_sample_data()