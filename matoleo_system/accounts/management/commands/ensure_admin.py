"""
Management command to create or update the admin superuser.
Usage: python manage.py ensure_admin
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import os


class Command(BaseCommand):
    help = 'Ensure admin superuser exists with the correct password'

    def handle(self, *args, **options):
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin123!@#')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

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
