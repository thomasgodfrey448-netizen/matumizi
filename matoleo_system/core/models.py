from django.db import models
from django.contrib.auth.models import User


class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    image = models.ImageField(upload_to='announcements/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Approver(models.Model):
    APPROVER_LEVEL_CHOICES = [
        ('first', 'First Approver'),
        ('second', 'Second Approver'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='approver_profile')
    level = models.CharField(max_length=10, choices=APPROVER_LEVEL_CHOICES)
    departments = models.ManyToManyField(Department, blank=True, 
                                        help_text='For first approvers only. Leave empty for second approvers')
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name_plural = 'Approvers'

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_level_display()})"

    def can_approve(self, request_obj):
        """Check if this approver can approve the request based on level and department"""
        if self.level == 'second':
            return True  # Second approvers can approve all
        if self.level == 'first':
            return request_obj.department in self.departments.all()
        return False


class Treasurer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='treasurer_profile')
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name_plural = 'Treasurers'

    def __str__(self):
        return f"{self.user.get_full_name()} (Treasurer)"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    registration_code_used = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} Profile"

    def is_admin_user(self):
        return self.user.is_staff or self.user.is_superuser

    def is_approver(self):
        return hasattr(self.user, 'approver_profile')

    def get_role(self):
        if self.user.is_superuser or self.user.is_staff:
            return 'admin'
        if hasattr(self.user, 'approver_profile'):
            return f"approver_{self.user.approver_profile.level}"
        return 'user'


class RegistrationCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_codes')
    created_at = models.DateTimeField(auto_now_add=True)
    max_uses = models.IntegerField(default=1)
    use_count = models.IntegerField(default=0)

    def __str__(self):
        return self.code

    def is_valid(self):
        return self.use_count < self.max_uses

    def is_valid_for_department(self, department):
        """Return True if this code is valid for the given department."""
        if self.department:
            return department is not None and self.department_id == department.id
        return True


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('pending_expense', 'Pending Expense'),
        ('pending_retirement', 'Pending Retirement'),
        ('approved_expense', 'Approved Expense'),
        ('approved_retirement', 'Approved Retirement'),
        ('rejected_expense', 'Rejected Expense'),
        ('rejected_retirement', 'Rejected Retirement'),
        ('paid_expense', 'Paid Expense'),
        ('paid_retirement', 'Paid Retirement'),
        ('general', 'General'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES, default='general')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.title}"
    
    def is_expired(self):
        """Check if notification has been read and is older than 24 hours"""
        if not self.is_read or not self.read_at:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() - self.read_at > timedelta(hours=24)
