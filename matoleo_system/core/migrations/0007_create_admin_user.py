from django.db import migrations


def create_admin_user(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    username = 'admin'
    email = 'admin@church.local'
    password = 'Admin@12345'

    try:
        if not User.objects.filter(username=username).exists():
            user = User(username=username, email=email, is_staff=True, is_superuser=True)
            user.set_password(password)
            user.save()
    except Exception:
        # On failure, don't block migrations; admin can be created manually later
        pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_notification_notification_type'),
    ]

    operations = [
        migrations.RunPython(create_admin_user, noop),
    ]
