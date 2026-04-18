from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('treasurer-dashboard/', views.treasurer_dashboard, name='treasurer_dashboard'),
    path('treasurer-dashboard/announcement/add/', views.add_announcement, name='treasurer_add_announcement'),
    path('treasurer-dashboard/announcement/<int:pk>/delete/', views.delete_announcement, name='treasurer_delete_announcement'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/department/add/', views.add_department, name='add_department'),
    path('admin-panel/department/<int:pk>/delete/', views.delete_department, name='delete_department'),
    path('admin-panel/approver/add/', views.add_approver, name='add_approver'),
    path('admin-panel/approver/<int:pk>/remove/', views.remove_approver, name='remove_approver'),
    path('admin-panel/treasurer/add/', views.add_treasurer, name='add_treasurer'),
    path('admin-panel/treasurer/<int:pk>/remove/', views.remove_treasurer, name='remove_treasurer'),
    path('admin-panel/reg-code/generate/', views.generate_reg_code, name='generate_reg_code'),
    path('admin-panel/reg-code/<int:pk>/delete/', views.delete_reg_code, name='delete_reg_code'),
    path('admin-panel/announcement/add/', views.add_announcement, name='add_announcement'),
    path('admin-panel/announcement/<int:pk>/delete/', views.delete_announcement, name='delete_announcement'),
    path('admin-panel/user/<int:pk>/toggle-staff/', views.toggle_user_staff, name='toggle_user_staff'),
    path('admin-panel/user/<int:pk>/delete/', views.delete_user, name='delete_user'),
    path('api/approver-info/', views.get_approver_info, name='get_approver_info'),
]
