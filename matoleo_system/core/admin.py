from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
from django.contrib import messages
import uuid
from .models import Announcement, Department, Approver, Treasurer, UserProfile, RegistrationCode, Notification


class GenerateCodesForm(forms.Form):
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        label="Department"
    )
    num_codes = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        label="Number of Codes"
    )


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active']

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']

@admin.register(Approver)
class ApproverAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'phone_number', 'is_active']
    list_filter = ['level', 'is_active']
    filter_horizontal = ['departments']
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone_number', 'is_active')
        }),
        ('Approver Configuration', {
            'fields': ('level', 'departments'),
            'description': 'First approvers: Select departments they can approve. Second approvers: Leave empty.'
        }),
    )

@admin.register(Treasurer)
class TreasurerAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'is_active']
    list_filter = ['is_active']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'department', 'is_approved']
    list_filter = ['is_approved']

@admin.register(RegistrationCode)
class RegistrationCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'display_department', 'use_count', 'max_uses', 'created_by', 'created_at']

    def display_department(self, obj):
        return obj.department.name if obj.department else "All Departments"
    display_department.short_description = "Department"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('generate-codes/', self.admin_site.admin_view(self.generate_codes_view), name='core_registrationcode_generate_codes'),
        ]
        return my_urls + urls

    def generate_codes_view(self, request):
        if request.method == 'POST':
            form = GenerateCodesForm(request.POST)
            if form.is_valid():
                department = form.cleaned_data['department']
                num_codes = form.cleaned_data['num_codes']
                for _ in range(num_codes):
                    code = str(uuid.uuid4())[:8].upper()
                    RegistrationCode.objects.create(
                        code=code,
                        department=department,
                        created_by=request.user,
                        max_uses=1
                    )
                self.message_user(request, f'Successfully generated {num_codes} registration codes for {department.name}.')
                return redirect('admin:core_registrationcode_changelist')
        else:
            form = GenerateCodesForm()
        return render(request, 'admin/core/registrationcode/generate_codes.html', {
            'form': form,
            'opts': self.model._meta,
            'site_header': self.admin_site.site_header,
            'site_title': self.admin_site.site_title,
        })

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'title', 'is_read', 'created_at']
    list_filter = ['is_read']
