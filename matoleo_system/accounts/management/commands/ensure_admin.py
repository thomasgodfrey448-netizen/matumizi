"""
Management command to create or update the admin superuser.
Usage: python manage.py ensure_admin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os


class Command(BaseCommand):
    help = 'Ensure admin superuser and optional default login user exist with the correct password'

    def handle(self, *args, **options):
        admin_username = (
            os.environ.get('ADMIN_USERNAME')
            or os.environ.get('admin_username')
            or os.environ.get('USERNAME')
            or os.environ.get('username')
            or 'admin'
        )
        admin_password = (
            os.environ.get('ADMIN_PASSWORD')
            or os.environ.get('admin_password')
            or os.environ.get('PASSWORD')
            or os.environ.get('password')
            or 'Admin123!@#'
        )
        admin_email = (
            os.environ.get('ADMIN_EMAIL')
            or os.environ.get('admin_email')
            or os.environ.get('EMAIL')
            or os.environ.get('email')
            or 'admin@example.com'
        )

        if User.objects.filter(username=admin_username).exists():
            admin = User.objects.get(username=admin_username)
            admin.set_password(admin_password)
            admin.email = admin_email
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ Admin user "{admin_username}" updated successfully')
            )
        else:
            User.objects.create_superuser(admin_username, admin_email, admin_password)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Admin user "{admin_username}" created successfully')
            )

        self.stdout.write(self.style.WARNING(f'  Username: {admin_username}'))
        self.stdout.write(self.style.WARNING(f'  Password: {admin_password}'))
        self.stdout.write(self.style.WARNING(f'  Email: {admin_email}'))

        default_username = os.environ.get('DEFAULT_USER_USERNAME') or os.environ.get('default_user_username')
        default_password = os.environ.get('DEFAULT_USER_PASSWORD') or os.environ.get('default_user_password')
        default_email = (
            os.environ.get('DEFAULT_USER_EMAIL')
            or os.environ.get('default_user_email')
            or os.environ.get('EMAIL')
            or os.environ.get('email')
            or 'user@example.com'
        )
        default_first_name = os.environ.get('DEFAULT_USER_FIRST_NAME', '')
        default_last_name = os.environ.get('DEFAULT_USER_LAST_NAME', '')

        if default_username and default_password:
            if User.objects.filter(username=default_username).exists():
                user = User.objects.get(username=default_username)
                user.set_password(default_password)
                user.email = default_email
                user.first_name = default_first_name
                user.last_name = default_last_name
                user.is_staff = False
                user.is_superuser = False
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Default user "{default_username}" updated successfully')
                )
            else:
                User.objects.create_user(
                    default_username,
                    default_email,
                    default_password,
                    first_name=default_first_name,
                    last_name=default_last_name,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Default user "{default_username}" created successfully')
                )
            self.stdout.write(self.style.WARNING(f'  Default user: {default_username}'))
        else:
            self.stdout.write('No default user credentials provided; skipping default user creation.')
