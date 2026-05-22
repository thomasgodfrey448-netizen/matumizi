import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a default admin user'

    def handle(self, *args, **options):
        username = (
            os.environ.get('ADMIN_USERNAME')
            or os.environ.get('ADMIN_USER')
            or os.environ.get('USERNAME')
            or os.environ.get('username')
            or 'admin'
        )
        email = (
            os.environ.get('ADMIN_EMAIL')
            or os.environ.get('EMAIL')
            or os.environ.get('email')
            or 'admin@church.local'
        )
        password = (
            os.environ.get('ADMIN_PASSWORD')
            or os.environ.get('ADMIN_PASS')
            or os.environ.get('PASSWORD')
            or os.environ.get('password')
            or 'Admin@12345'
        )

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Admin user "{username}" already exists')
            )
        else:
            User.objects.create_superuser(username, email, password)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Admin user created successfully:\n')
                + f'  Username: {username}\n'
                + f'  Password: {password}\n'
                + f'  Email: {email}'
            )
