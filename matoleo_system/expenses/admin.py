from django.contrib import admin
from .models import ExpenseRequest, ExpenseItem, Budget

class ExpenseItemInline(admin.TabularInline):
    model = ExpenseItem
    extra = 1

@admin.register(ExpenseRequest)
class ExpenseRequestAdmin(admin.ModelAdmin):
    list_display = ['form_number', 'first_name', 'last_name', 'department', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'department']
    inlines = [ExpenseItemInline]

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['department', 'church_budget', 'contribution1_name', 'contribution1_amount', 'contribution2_name', 'contribution2_amount']
    list_filter = ['department']
