from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from core.models import Department, Approver, UserProfile
from .models import ExpenseRequest


class DashboardFilteringTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create departments
        self.dept_a = Department.objects.create(name='Department A', is_active=True)
        self.dept_b = Department.objects.create(name='Department B', is_active=True)

        # Create users
        self.admin_user = User.objects.create_user(username='admin', password='admin123', is_staff=True)
        self.first_approver_user = User.objects.create_user(username='first_approver', password='pass123')
        self.second_approver_user = User.objects.create_user(username='second_approver', password='pass123')

        # Create approver profiles
        self.first_approver = Approver.objects.create(
            user=self.first_approver_user,
            level='first',
            is_active=True
        )
        self.first_approver.departments.add(self.dept_a)  # Only assigned to dept A

        self.second_approver = Approver.objects.create(
            user=self.second_approver_user,
            level='second',
            is_active=True
        )

        # Create regular user
        self.regular_user = User.objects.create_user(username='regular', password='pass123')
        profile, _ = UserProfile.objects.get_or_create(user=self.regular_user)
        profile.department = self.dept_a
        profile.is_approved = True
        profile.save()

        # Create test expense requests
        self.expense_a = ExpenseRequest.objects.create(
            submitted_by=self.regular_user,
            department=self.dept_a,
            first_name='John',
            last_name='Doe',
            phone_number='+1234567890',
            date=date.today(),
            reason='Test expense A',
            total_amount=100.00,
            status='submitted'
        )

        self.expense_b = ExpenseRequest.objects.create(
            submitted_by=self.regular_user,
            department=self.dept_b,
            first_name='Jane',
            last_name='Smith',
            phone_number='+1234567890',
            date=date.today(),
            reason='Test expense B',
            total_amount=200.00,
            status='submitted'
        )

    def test_first_approver_sees_only_assigned_department(self):
        """First approver should only see expenses from their assigned departments"""
        self.client.login(username='first_approver', password='pass123')
        response = self.client.get('/expenses/')
        self.assertEqual(response.status_code, 200)

        # Should contain expense from dept A (John Doe) but not dept B (Jane Smith)
        self.assertContains(response, 'John Doe')
        self.assertNotContains(response, 'Jane Smith')

    def test_second_approver_sees_all_departments(self):
        """Second approver should see expenses from all departments"""
        self.client.login(username='second_approver', password='pass123')
        response = self.client.get('/expenses/')
        self.assertEqual(response.status_code, 200)

        # Should contain expenses from both departments
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Smith')

    def test_admin_sees_all_departments(self):
        """Admin should see expenses from all departments"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/expenses/')
        self.assertEqual(response.status_code, 200)

        # Should contain expenses from both departments
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Smith')

    def test_regular_user_sees_only_own_expenses(self):
        """Regular user should only see their own expenses"""
        self.client.login(username='regular', password='pass123')
        response = self.client.get('/expenses/')
        self.assertEqual(response.status_code, 200)

        # Should contain both expenses since they were created by this user
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Jane Smith')
