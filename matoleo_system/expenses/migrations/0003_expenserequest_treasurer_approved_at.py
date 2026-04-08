# Generated migration for treasurer_approved_at field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0002_expenserequest_first_approver_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='expenserequest',
            name='treasurer_approved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
