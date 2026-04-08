from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import Department, RegistrationCode, UserProfile


class RegistrationLoginDepartmentValidationTests(TestCase):
    def setUp(self):
        self.department_a = Department.objects.create(name='Department A', code='A', is_active=True)
        self.department_b = Department.objects.create(name='Department B', code='B', is_active=True)
        self.admin_user = User.objects.create_user(username='admin', password='admin123', is_staff=True)
        self.reg_code = RegistrationCode.objects.create(
            code='DEPTA123',
            department=self.department_a,
            created_by=self.admin_user,
            max_uses=5,
        )
        self.client = Client()

    def test_registration_fails_when_department_mismatch(self):
        response = self.client.post('/accounts/register/', {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'username': 'alice',
            'phone_number': '+1234567890',
            'password': 'password123',
            'confirm_password': 'password123',
            'registration_code': self.reg_code.code,
            'department': str(self.department_b.id),
        })
        self.assertContains(response, 'Selected department does not match registration code')
        self.assertFalse(User.objects.filter(username='alice').exists())

    def test_login_fails_when_user_profile_department_mismatch(self):
        user = User.objects.create_user(username='bob', password='password123')
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone_number = '+1234567890'
        profile.department = self.department_b
        profile.registration_code_used = self.reg_code.code
        profile.is_approved = True
        profile.save()
        response = self.client.post('/accounts/login/', {
            'username': user.username,
            'password': 'password123',
        })
        self.assertContains(response, 'Your registration code does not match your selected department.')
        self.assertNotIn('_auth_user_id', self.client.session)

# Create your tests here.
