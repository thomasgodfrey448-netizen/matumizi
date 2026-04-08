from django.contrib import admin
from .models import RetirementForm, RetirementItem

class RetirementItemInline(admin.TabularInline):
    model = RetirementItem
    extra = 1

@admin.register(RetirementForm)
class RetirementFormAdmin(admin.ModelAdmin):
    list_display = ['form_number', 'first_name', 'last_name', 'department', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'department']
    inlines = [RetirementItemInline]
