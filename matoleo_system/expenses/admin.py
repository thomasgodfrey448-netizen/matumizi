from django.contrib import admin
from .models import ExpenseRequest, ExpenseItem

class ExpenseItemInline(admin.TabularInline):
    model = ExpenseItem
    extra = 1

@admin.register(ExpenseRequest)
class ExpenseRequestAdmin(admin.ModelAdmin):
    list_display = ['form_number', 'first_name', 'last_name', 'department', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'department']
    inlines = [ExpenseItemInline]
