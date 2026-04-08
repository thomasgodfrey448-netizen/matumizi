# Generated migration for adding payment_status field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_expenserequest_treasurer_approved_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='expenserequest',
            name='payment_status',
            field=models.CharField(
                choices=[('unpaid', 'Unpaid'), ('paid', 'Paid')],
                default='unpaid',
                max_length=20,
            ),
        ),
    ]
