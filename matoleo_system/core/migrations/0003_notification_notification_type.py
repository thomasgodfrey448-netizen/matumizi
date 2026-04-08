# Generated migration for adding notification_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_approver_options_remove_approver_department_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('pending_expense', 'Pending Expense'),
                    ('pending_retirement', 'Pending Retirement'),
                    ('approved_expense', 'Approved Expense'),
                    ('approved_retirement', 'Approved Retirement'),
                    ('rejected_expense', 'Rejected Expense'),
                    ('rejected_retirement', 'Rejected Retirement')
                ],
                default='pending_expense',
                max_length=20
            ),
        ),
    ]
