from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.reports_dashboard, name='dashboard'),
    path('expenses/', views.expenses_report, name='expenses'),
    path('retirement/', views.retirement_report, name='retirement'),
    path('download/expenses/', views.download_expense_report, name='download_expenses'),
    path('download/retirement/', views.download_retirement_report, name='download_retirement'),
]
