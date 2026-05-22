from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a default admin user'

    def handle(self, *args, **options):
        username = 'admin'
        email = 'admin@church.local'
        password = 'Admin@12345'

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
