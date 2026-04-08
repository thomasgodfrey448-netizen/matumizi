from django.urls import path
from . import views

app_name = 'retirement'

urlpatterns = [
    path('', views.retirement_dashboard, name='dashboard'),
    path('new/', views.create_retirement, name='create'),
    path('api/approver/<int:department_id>/', views.get_first_approver, name='get_approver'),
    path('<int:pk>/', views.retirement_detail, name='detail'),
    path('<int:pk>/edit/', views.edit_retirement, name='edit'),
    path('<int:pk>/delete/', views.delete_retirement, name='delete'),
    path('<int:pk>/submit/', views.submit_retirement, name='submit'),
    path('<int:pk>/approve/', views.approve_retirement, name='approve'),
    path('<int:pk>/download/', views.download_retirement_pdf, name='download'),
    path('<int:pk>/download_payment/', views.download_payment_pdf_retirement, name='download_payment'),
    path('<int:pk>/update_payment/', views.update_payment_retirement, name='update_payment'),
]
