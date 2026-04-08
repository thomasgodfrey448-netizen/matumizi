from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('', views.expense_dashboard, name='dashboard'),
    path('new/', views.create_expense, name='create'),
    path('api/approver/<int:department_id>/', views.get_first_approver, name='get_approver'),
    path('<int:pk>/', views.expense_detail, name='detail'),
    path('<int:pk>/edit/', views.edit_expense, name='edit'),
    path('<int:pk>/delete/', views.delete_expense, name='delete'),
    path('<int:pk>/submit/', views.submit_expense, name='submit'),
    path('<int:pk>/approve/', views.approve_expense, name='approve'),
    path('<int:pk>/download/', views.download_expense_pdf, name='download'),
    path('<int:pk>/download_payment/', views.download_payment_pdf, name='download_payment'),
    path('<int:pk>/update_payment/', views.update_payment, name='update_payment'),
]
