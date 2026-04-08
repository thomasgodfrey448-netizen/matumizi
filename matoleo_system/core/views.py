from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import models
from django.urls import resolve, Resolver404
from urllib.parse import urlparse
from .models import Announcement, Department, Approver, Treasurer, UserProfile, RegistrationCode, Notification
from django.contrib.auth.models import User
import uuid


@login_required
def home(request):
    announcements = Announcement.objects.filter(is_active=True).order_by('-created_at')[:10]
    
    # Check if user is approver or treasurer
    is_approver = hasattr(request.user, 'approver_profile')
    is_treasurer = hasattr(request.user, 'treasurer_profile')
    is_admin = request.user.is_staff or request.user.is_superuser
    
    # Get unread notifications count
    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    return render(request, 'core/home.html', {
        'announcements': announcements,
        'is_approver': is_approver,
        'is_treasurer': is_treasurer,
        'is_admin': is_admin,
        'unread_notifications_count': unread_notifications_count,
    })


@login_required
def notifications_view(request):
    from django.utils import timezone
    from datetime import timedelta
    
    all_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Filter out expired read notifications (read for more than 24 hours)
    cutoff_time = timezone.now() - timedelta(hours=24)
    notifications = all_notifications.filter(
        models.Q(is_read=False) | models.Q(read_at__isnull=True) | models.Q(read_at__gt=cutoff_time)
    )
    
    unread_count = notifications.filter(is_read=False).count()
    read_count = notifications.filter(is_read=True).count()
    
    # Don't auto-mark as read - let user click to mark individual notifications
    
    return render(request, 'core/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
        'read_count': read_count,
    })


from django.views.decorators.csrf import csrf_exempt

@login_required
@csrf_exempt
def mark_notification_read(request, pk):
    from django.utils import timezone
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    
    # Only mark as read if not already read
    if not notif.is_read:
        notif.is_read = True
        notif.read_at = timezone.now()
        notif.save()
    
    # Redirect to the notification link or back to notifications
    if notif.link:
        try:
            link = str(notif.link).strip()
            if not link:
                raise ValueError('Empty notification link')

            parsed = urlparse(link)
            if parsed.scheme or parsed.netloc:
                raise ValueError('External links are not supported')

            if not link.startswith('/'):
                link = '/' + link

            try:
                resolve(link)
            except Resolver404:
                raise ValueError('Notification link does not resolve to a valid page')

            return redirect(link)
        except Exception as e:
            # Log the error for debugging
            print(f"Notification redirect failed for notification {notif.pk} link='{notif.link}': {str(e)}")
            messages.error(request, 'Could not access the linked page. Please navigate manually.')
            return redirect('core:notifications')
    return redirect('core:notifications')


@login_required
def treasurer_dashboard(request):
    # Check if user is treasurer
    if not hasattr(request.user, 'treasurer_profile'):
        messages.error(request, 'Access denied. Treasurer privileges required.')
        return redirect('core:home')
    
    # Get unread notifications count
    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    
    # Get pending approvals for treasurer
    from expenses.models import ExpenseRequest
    from retirement.models import RetirementForm
    
    # Get requests that are approved but not paid
    pending_payments_expenses = ExpenseRequest.objects.filter(
        status='approved', 
        is_paid=False
    ).order_by('-submitted_at')
    
    pending_payments_retirement = RetirementForm.objects.filter(
        status='approved', 
        is_paid=False
    ).order_by('-submitted_at')
    
    # Get recently paid requests
    recent_payments_expenses = ExpenseRequest.objects.filter(
        is_paid=True
    ).order_by('-paid_at')[:10]
    
    recent_payments_retirement = RetirementForm.objects.filter(
        is_paid=True
    ).order_by('-paid_at')[:10]
    
    # Get announcements for posting
    announcements = Announcement.objects.all().order_by('-created_at')[:5]
    
    return render(request, 'core/treasurer_dashboard.html', {
        'pending_payments_expenses': pending_payments_expenses,
        'pending_payments_retirement': pending_payments_retirement,
        'recent_payments_expenses': recent_payments_expenses,
        'recent_payments_retirement': recent_payments_retirement,
        'announcements': announcements,
        'unread_notifications_count': unread_notifications_count,
    })


@staff_member_required
def admin_dashboard(request):
    
    # Get admins  
    admins = User.objects.filter(is_staff=True, is_superuser=False).order_by('-date_joined')
    
    # Get regular users
    regular_users = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')
    
    # Get first approvers
    first_approvers = Approver.objects.filter(level='first').select_related('user').order_by('user__first_name')
    
    # Get second approvers
    second_approvers = Approver.objects.filter(level='second').select_related('user').order_by('user__first_name')
    
    # Get treasurers
    treasurers = Treasurer.objects.select_related('user').order_by('user__first_name')
    
    # Other data
    departments = Department.objects.all().order_by('name')
    reg_codes = RegistrationCode.objects.all().order_by('-created_at')
    announcements = Announcement.objects.all().order_by('-created_at')
    
    # Get pending notifications count  
    from expenses.models import ExpenseRequest
    from retirement.models import RetirementForm
    
    pending_approvals = (
        ExpenseRequest.objects.filter(status='submitted').count() +
        ExpenseRequest.objects.filter(status='first_approved').count() +
        ExpenseRequest.objects.filter(status='second_approved').count() +
        RetirementForm.objects.filter(status='submitted').count() +
        RetirementForm.objects.filter(status='first_approved').count() +
        RetirementForm.objects.filter(status='second_approved').count()
    )
    
    return render(request, 'core/admin_dashboard.html', {
        'regular_users': regular_users,
        'admins': admins,
        'first_approvers': first_approvers,
        'second_approvers': second_approvers,
        'treasurers': treasurers,
        'departments': departments,
        'reg_codes': reg_codes,
        'announcements': announcements,
        'pending_approvals': pending_approvals,
    })


@staff_member_required
def add_department(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        if name:
            Department.objects.get_or_create(name=name, defaults={'code': code})
            messages.success(request, f'Department "{name}" added.')
        else:
            messages.error(request, 'Department name is required.')
    return redirect('core:admin_dashboard')


@staff_member_required
def delete_department(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    dept.delete()
    messages.success(request, 'Department deleted.')
    return redirect('core:admin_dashboard')


@staff_member_required
def add_approver(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        level = request.POST.get('level')
        dept_ids = request.POST.getlist('departments')
        phone = request.POST.get('phone_number', '').strip()
        try:
            user = User.objects.get(id=user_id)
            approver, created = Approver.objects.get_or_create(
                user=user,
                defaults={'level': level, 'phone_number': phone, 'is_active': True}
            )
            if not created:
                approver.level = level
                approver.phone_number = phone
                approver.is_active = True
                approver.save()
            
            # Add departments for first approvers
            if level == 'first' and dept_ids:
                approver.departments.set(dept_ids)
            elif level == 'second':
                approver.departments.clear()
            
            messages.success(request, f'{user.get_full_name()} set as {level} approver.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    return redirect('core:admin_dashboard')


@staff_member_required
def remove_approver(request, pk):
    approver = get_object_or_404(Approver, pk=pk)
    approver.delete()
    messages.success(request, 'Approver removed.')
    return redirect('core:admin_dashboard')


@staff_member_required
def add_treasurer(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        phone = request.POST.get('phone_number', '').strip()
        try:
            user = User.objects.get(id=user_id)
            treasurer, created = Treasurer.objects.get_or_create(
                user=user,
                defaults={'phone_number': phone, 'is_active': True}
            )
            if not created:
                treasurer.phone_number = phone
                treasurer.is_active = True
                treasurer.save()
            messages.success(request, f'{user.get_full_name()} set as treasurer.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    return redirect('core:admin_dashboard')


@staff_member_required
def remove_treasurer(request, pk):
    treasurer = get_object_or_404(Treasurer, pk=pk)
    treasurer.delete()
    messages.success(request, 'Treasurer removed.')
    return redirect('core:admin_dashboard')


@staff_member_required
def generate_reg_code(request):
    if request.method == 'POST':
        max_uses = int(request.POST.get('max_uses', 1))
        department_id = request.POST.get('department')
        department = None
        if department_id:
            try:
                department = Department.objects.get(pk=department_id)
            except Department.DoesNotExist:
                department = None
        code = str(uuid.uuid4()).upper()[:12]
        RegistrationCode.objects.create(
            code=code,
            created_by=request.user,
            max_uses=max_uses,
            department=department
        )
        if department:
            messages.success(request, f'Registration code generated for {department.name}: {code}')
        else:
            messages.success(request, f'Registration code generated for all departments: {code}')
    return redirect('core:admin_dashboard')


@staff_member_required
def delete_reg_code(request, pk):
    code = get_object_or_404(RegistrationCode, pk=pk)
    code.delete()
    messages.success(request, 'Registration code deleted.')
    return redirect('core:admin_dashboard')


@staff_member_required
def add_announcement(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')
        if title and content:
            Announcement.objects.create(
                title=title, content=content, image=image,
                created_by=request.user, is_active=True
            )
            messages.success(request, 'Announcement added.')
        else:
            messages.error(request, 'Title and content are required.')
    return redirect('core:admin_dashboard')


@staff_member_required
def delete_announcement(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    ann.delete()
    messages.success(request, 'Announcement deleted.')
    return redirect('core:admin_dashboard')


@staff_member_required
def toggle_user_staff(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user != request.user:
        user.is_staff = not user.is_staff
        user.save()
        messages.success(request, f'Staff status updated for {user.username}.')
    return redirect('core:admin_dashboard')


@staff_member_required
def delete_user(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user != request.user:
        user.delete()
        messages.success(request, 'User deleted.')
    return redirect('core:admin_dashboard')


def get_approver_info(request):
    dept_id = request.GET.get('department_id')
    if dept_id:
        approvers = Approver.objects.filter(
            department_id=dept_id, level='first', is_active=True
        ).select_related('user')
        data = [{'name': a.user.get_full_name(), 'phone': a.phone_number} for a in approvers]
        return JsonResponse({'approvers': data})
    return JsonResponse({'approvers': []})

