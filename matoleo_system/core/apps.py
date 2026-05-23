import logging
import os
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals
        self.ensure_admin_user()

    def ensure_admin_user(self):
        if not os.environ.get('ADMIN_USERNAME') or not os.environ.get('ADMIN_PASSWORD'):
            return

        if any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'collectstatic', 'test', 'shell', 'dbshell', 'flush']):
            return

        username = os.environ.get('ADMIN_USERNAME', '').strip()
        password = os.environ.get('ADMIN_PASSWORD', '').strip()
        email = os.environ.get('ADMIN_EMAIL', '').strip() or 'admin@example.com'

        if not username or not password:
            return

        try:
            from django.contrib.auth.models import User
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                user.set_password(password)
                user.email = email
                user.is_staff = True
                user.is_superuser = True
                user.save()
                logger.info(f'Updated admin user: {username}')
            else:
                User.objects.create_superuser(username, email, password)
                logger.info(f'Created admin user: {username}')
        except Exception as e:
            logger.warning(f'Unable to ensure admin user on startup: {e}', exc_info=True)
