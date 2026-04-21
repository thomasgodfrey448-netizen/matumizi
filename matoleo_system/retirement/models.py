from django.db import models
from django.contrib.auth.models import User
from core.models import Department


class RetirementForm(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('first_approved', 'First Approved'),
        ('second_approved', 'Second Approved'),
        ('approved', 'Closed'),
        ('paid', 'Paid'),
        ('rejected', 'Not Approved'),
        ('rejected_for_editing', 'Rejected for Editing'),
        ('open', 'Open'),
    ]

    form_number = models.CharField(max_length=30, unique=True, blank=True)
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='retirement_forms')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    date_of_request = models.DateField()
    date_of_retirement = models.DateField()
    reason = models.TextField()
    exp_request_form_no = models.CharField(max_length=100, default='N/A')
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)

    # Approval tracking
    first_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='first_approved_retirements')
    first_approver_name = models.CharField(max_length=200, blank=True)
    first_approver_phone = models.CharField(max_length=20, blank=True)
    first_approved_at = models.DateTimeField(null=True, blank=True)
    
    second_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='second_approved_retirements')
    second_approver_name = models.CharField(max_length=200, blank=True)
    second_approver_phone = models.CharField(max_length=20, blank=True)
    second_approved_at = models.DateTimeField(null=True, blank=True)
    
    treasurer_name = models.CharField(max_length=200, blank=True)
    treasurer_phone = models.CharField(max_length=20, blank=True)
    treasurer_approved_at = models.DateTimeField(null=True, blank=True)
    
    admin_approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='admin_approved_retirements')
    admin_approved_at = models.DateTimeField(null=True, blank=True)

    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='paid_retirements')

    payment_method = models.CharField(max_length=50, blank=True, choices=[
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('mpesa', 'M-Pesa'),
    ])
    payment_date = models.DateField(null=True, blank=True)
    reference_number = models.CharField(max_length=50, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Retirement Form #{self.form_number} - {self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.form_number:
            import datetime
            year = datetime.date.today().year
            count = RetirementForm.objects.filter(
                created_at__year=year
            ).count() + 1
            self.form_number = f"RET-{year}-{count:04d}"
        super().save(*args, **kwargs)

    def get_approval_ticks(self):
        if self.status == 'approved':
            return 'approved'
        elif self.status == 'rejected':
            return 'rejected'
        elif self.status == 'second_approved':
            return 'two_ticks'
        elif self.status == 'first_approved':
            return 'one_tick'
        return 'none'

    def can_edit(self):
        return self.status in ['draft', 'rejected_for_editing']
    
    def get_approval_status(self):
        """Return detailed approval status for display"""
        statuses = {
            'first_approver': self.first_approved_at is not None,
            'second_approver': self.second_approved_at is not None,
        }
        return statuses


class RetirementItem(models.Model):
    retirement_form = models.ForeignKey(RetirementForm, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.description}: {self.amount}"
