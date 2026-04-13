from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import ExpenseRequest
from core.models import Notification


@receiver(pre_save, sender=ExpenseRequest)
def pre_save_expense_request(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_is_paid = False
        return
    try:
        existing = ExpenseRequest.objects.get(pk=instance.pk)
        instance._old_is_paid = existing.is_paid
    except ExpenseRequest.DoesNotExist:
        instance._old_is_paid = False


@receiver(post_save, sender=ExpenseRequest)
def post_save_expense_request(sender, instance, created, **kwargs):
    if created:
        return
    old_is_paid = getattr(instance, '_old_is_paid', False)
    new_is_paid = instance.is_paid

    if not old_is_paid and new_is_paid:
        Notification.objects.create(
            recipient=instance.submitted_by,
            title='Expense Request Marked Paid',
            message=f"Your expense request {instance.form_number} has been marked as paid.",
            link=f"/expenses/{instance.id}/",
            notification_type='approved_expense',
        )
