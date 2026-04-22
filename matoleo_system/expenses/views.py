from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db import transaction, models
from django.contrib.auth.models import User
from .models import ExpenseRequest, ExpenseItem, Budget
import calendar
import logging
from datetime import datetime, date
from core.models import Department, Approver, Treasurer, Notification, UserProfile
from core.pdf_utils import expense_to_pdf, payment_voucher_pdf
from django.conf import settings
import io
import os
import traceback

logger = logging.getLogger(__name__)


def send_notification(recipient, title, message, link='', notification_type='general'):
    # Ensure link is absolute
    if link and not link.startswith('/'):
        link = '/' + link
    Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        link=link,
        notification_type=notification_type,
    )


@login_required
def get_first_approver(request, department_id):
    """API endpoint to get the first approver for a department"""
    try:
        department = Department.objects.get(id=department_id)
        approver = Approver.objects.filter(
            departments=department,
            level='first',
            is_active=True
        ).select_related('user').first()
        
        if approver:
            return JsonResponse({
                'success': True,
                'approver_name': approver.user.get_full_name(),
                'approver_phone': approver.phone_number,
                'approver_id': approver.user.id,
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No first approver assigned to this department'
            })
    except Department.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Department not found'
        })


@login_required
def get_budget_options(request, department_id):
    """API endpoint to get available budget options for a department"""
    try:
        options = build_budget_options_for_department(department_id)
        return JsonResponse({'success': True, 'options': options})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def normalize_budget_choice(choice):
    if not choice:
        return choice
    normalized = choice.strip().lower()
    if normalized == 'department':
        return 'church_budget'
    return normalized


def build_budget_options_for_department(department):
    budget_options = [{'value': 'church_budget', 'label': 'Church Budget'}]
    budget = Budget.objects.filter(department=department).first() if department else None

    if budget:
        if budget.contribution1_name and budget.contribution1_amount > 0:
            budget_options.append({'value': 'contribution1', 'label': budget.contribution1_name})
        if budget.contribution2_name and budget.contribution2_amount > 0:
            budget_options.append({'value': 'contribution2', 'label': budget.contribution2_name})
    budget_options.append({'value': 'mk', 'label': 'MK'})
    return budget_options


@login_required
def expense_dashboard(request):
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if is_admin or is_treasurer:
        # Admins and Treasurers see all records
        requests = ExpenseRequest.objects.all().select_related('submitted_by', 'department')
    elif is_approver:
        approver = user.approver_profile
        if approver.level == 'first':
            # First approvers see only records from their assigned departments
            requests = ExpenseRequest.objects.filter(
                department__in=approver.departments.all()
            ).select_related('submitted_by', 'department')
        else:
            # Second approvers see all records
            requests = ExpenseRequest.objects.all().select_related('submitted_by', 'department')
    else:
        requests = ExpenseRequest.objects.filter(submitted_by=user).select_related('department')

    selected_month = request.GET.get('month', '').strip()
    today = timezone.localdate()

    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
            start_date = date(year, month, 1)
            end_day = calendar.monthrange(year, month)[1]
            end_date = date(year, month, end_day)
        except (ValueError, calendar.IllegalMonthError):
            start_date = today.replace(day=1)
            end_date = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            selected_month = today.strftime('%Y-%m')
    else:
        start_date = today.replace(day=1)
        end_date = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        selected_month = today.strftime('%Y-%m')

    requests = requests.filter(date__gte=start_date, date__lte=end_date)

    approved_requests = requests.filter(status__in=['approved', 'paid'])
    pending_requests = requests.exclude(status__in=['approved', 'paid'])

    return render(request, 'expenses/dashboard.html', {
        'requests': requests,
        'pending_count': pending_requests.count(),
        'approved_count': approved_requests.count(),
        'is_approver': is_approver,
        'is_admin': is_admin,
        'is_treasurer': is_treasurer,
        'selected_month': selected_month,
        'date_from': start_date,
        'date_to': end_date,
    })


@login_required
def budget_view(request):
    user = request.user
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')
    
    # Get user's department
    try:
        profile = UserProfile.objects.get(user=user)
        user_department = profile.department
    except UserProfile.DoesNotExist:
        user_department = None
    
    # Filter budgets based on permissions
    if is_admin or is_treasurer:
        budgets = Budget.objects.all().select_related('department')
    else:
        if user_department:
            budgets = Budget.objects.filter(department=user_department).select_related('department')
        else:
            budgets = Budget.objects.none()
    
    # Get filter parameters
    selected_month = request.GET.get('month', '').strip()
    show_all = request.GET.get('all', '') == 'true'
    today = timezone.localdate()
    
    if selected_month and not show_all:
        try:
            year, month = map(int, selected_month.split('-'))
            start_date = date(year, month, 1)
            end_date = date(year, month, calendar.monthrange(year, month)[1])
        except (ValueError, calendar.IllegalMonthError):
            start_date = today.replace(day=1)
            end_date = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            selected_month = today.strftime('%Y-%m')
    else:
        if show_all:
            start_date = None
            end_date = None
            selected_month = ''
        else:
            start_date = today.replace(day=1)
            end_date = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            selected_month = today.strftime('%Y-%m')
    
    budget_data = []
    total_budget = 0
    total_expenses = 0
    total_balance = 0
    
    for budget in budgets:
        dept_data = {
            'department': budget.department,
            'church_budget': {
                'allocated': budget.church_budget,
                'used': 0,
                'balance': budget.church_budget,
                'forms': []
            },
            'contribution1': {
                'name': budget.contribution1_name,
                'allocated': budget.contribution1_amount,
                'used': 0,
                'balance': budget.contribution1_amount,
                'forms': []
            },
            'contribution2': {
                'name': budget.contribution2_name,
                'allocated': budget.contribution2_amount,
                'used': 0,
                'balance': budget.contribution2_amount,
                'forms': []
            },
            'mk': {
                'allocated': 0,  # MK has no limit
                'used': 0,
                'balance': 0,
                'forms': []
            }
        }
        
        # Get paid forms for this department
        forms_query = ExpenseRequest.objects.filter(
            department=budget.department,
            status__in=['approved', 'paid']
        ).select_related('submitted_by')
        
        if start_date and end_date:
            forms_query = forms_query.filter(date__gte=start_date, date__lte=end_date)
        
        forms = forms_query.order_by('-paid_at')
        
        for form in forms:
            budget_type = form.budget_choice
            if budget_type in dept_data:
                dept_data[budget_type]['used'] += form.total_amount
                dept_data[budget_type]['balance'] = dept_data[budget_type]['allocated'] - dept_data[budget_type]['used']
                dept_data[budget_type]['forms'].append(form)
        
        # Calculate totals
        dept_total_budget = sum([dept_data[bt]['allocated'] for bt in ['church_budget', 'contribution1', 'contribution2']])
        dept_total_expenses = sum([dept_data[bt]['used'] for bt in ['church_budget', 'contribution1', 'contribution2', 'mk']])
        dept_total_balance = dept_total_budget - (dept_total_expenses - dept_data['mk']['used'])  # MK doesn't count against balance
        
        budget_data.append({
            'department': budget.department,
            'data': dept_data,
            'total_budget': dept_total_budget,
            'total_expenses': dept_total_expenses,
            'total_balance': dept_total_balance,
        })
        
        total_budget += dept_total_budget
        total_expenses += dept_total_expenses
        total_balance += dept_total_balance
    
    return render(request, 'expenses/budget.html', {
        'budget_data': budget_data,
        'total_budget': total_budget,
        'total_expenses': total_expenses,
        'total_balance': total_balance,
        'selected_month': selected_month,
        'show_all': show_all,
        'date_from': start_date,
        'date_to': end_date,
        'is_admin': is_admin,
        'is_treasurer': is_treasurer,
    })


@login_required
def create_expense(request):
    if hasattr(request.user, 'approver_profile'):
        messages.error(request, 'Approvers cannot create expense requests.')
        return redirect('expenses:dashboard')

    departments = Department.objects.filter(is_active=True)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Ensure the user's department still exists
    if profile.department_id:
        if not Department.objects.filter(id=profile.department_id).exists():
            profile.department_id = None
            profile.save()

    # Get initial budget options
    budget_options = build_budget_options_for_department(profile.department)

    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            phone = request.POST.get('phone_number', '').strip()
            dept_id = request.POST.get('department')
            request_date = request.POST.get('date')
            reason = request.POST.get('reason', '').strip()
            budget_choice = normalize_budget_choice(request.POST.get('budget_choice', ''))
            descriptions = request.POST.getlist('item_description[]')
            amounts = request.POST.getlist('item_amount[]')

            logger.info(f"Expense form submission: budget_choice={budget_choice}, dept_id={dept_id}")

            if not all([first_name, last_name, phone, dept_id, request_date, reason, budget_choice]):
                messages.error(request, 'Please fill all required fields.')
                return render(request, 'expenses/form.html', {
                    'departments': departments,
                    'profile': profile,
                    'action': 'create',
                    'today_date': date.today().isoformat(),
                    'budget_options': budget_options,
                })

            try:
                dept = Department.objects.get(id=dept_id)
            except Department.DoesNotExist:
                messages.error(request, 'Invalid department.')
                return render(request, 'expenses/form.html', {
                    'departments': departments,
                    'profile': profile,
                    'action': 'create',
                    'today_date': date.today().isoformat(),
                    'budget_options': budget_options,
                })

            # Validate budget choice
            allowed_budgets = [opt['value'] for opt in budget_options]
            if budget_choice not in allowed_budgets:
                messages.error(request, 'Invalid budget choice for this department.')
                return render(request, 'expenses/form.html', {
                    'departments': departments,
                    'profile': profile,
                    'action': 'create',
                    'today_date': date.today().isoformat(),
                    'budget_options': budget_options,
                })

            total = 0
            items_data = []
            for i, (desc, amt) in enumerate(zip(descriptions, amounts)):
                desc = desc.strip()
                if desc:
                    try:
                        amt_val = float(amt) if amt else 0
                        if amt_val < 0:
                            messages.error(request, 'Item amounts cannot be negative.')
                            return redirect(request.path)
                        total += amt_val
                        items_data.append((desc, amt_val, i))
                    except ValueError:
                        messages.error(request, 'Invalid amount value. Please enter a valid number.')
                        return redirect(request.path)

            # Validate budget choice and balance
            if budget_choice != 'mk':
                selected_budget_label = next((opt['label'] for opt in budget_options if opt['value'] == budget_choice), budget_choice.replace('_', ' ').title())
                budget = Budget.objects.filter(department=dept).first()
                if not budget:
                    messages.error(request, 'No budget configured for this department.')
                    return render(request, 'expenses/form.html', {
                        'departments': departments,
                        'profile': profile,
                        'action': 'create',
                        'today_date': date.today().isoformat(),
                        'budget_options': budget_options,
                    })

                if budget_choice == 'church_budget':
                    available = budget.church_budget
                elif budget_choice == 'contribution1':
                    available = budget.contribution1_amount
                elif budget_choice == 'contribution2':
                    available = budget.contribution2_amount
                else:
                    available = 0
                
                used_amount = ExpenseRequest.objects.filter(
                    department=dept,
                    budget_choice=budget_choice,
                    status__in=['approved', 'paid']
                ).aggregate(total=models.Sum('total_amount'))['total'] or 0
                
                if total > (available - used_amount):
                    messages.error(request, f'Insufficient balance in {selected_budget_label}. Available: TZS {available - used_amount:,.0f}, Requested: TZS {total:,.0f}')
                    return render(request, 'expenses/form.html', {
                        'departments': departments,
                        'profile': profile,
                        'action': 'create',
                        'today_date': date.today().isoformat(),
                        'budget_options': budget_options,
                    })

            with transaction.atomic():
                expense = ExpenseRequest.objects.create(
                    submitted_by=request.user,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone,
                    department=dept,
                    date=request_date,
                    reason=reason,
                    total_amount=total,
                    budget_choice=budget_choice,
                    status='draft',
                )
                for desc, amt, order in items_data:
                    ExpenseItem.objects.create(
                        expense_request=expense,
                        description=desc,
                        amount=amt,
                        order=order,
                    )

            try:
                messages.success(request, f'Expense request {expense.form_number} created as draft.')
            except Exception as e:
                logger.error(f"Error creating success message: {e}")
            
            try:
                return redirect('expenses:detail', pk=expense.pk)
            except Exception as e:
                logger.error(f"Error redirecting to detail page: {e}\n{traceback.format_exc()}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error in create_expense POST: {e}\n{traceback.format_exc()}")
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return render(request, 'expenses/form.html', {
                'departments': departments,
                'profile': profile,
                'action': 'create',
                'today_date': date.today().isoformat(),
                'budget_options': budget_options,
            })

    today_date = date.today().isoformat()
    second_approver = Approver.objects.filter(level='second', is_active=True).select_related('user').first()
    treasurer = Treasurer.objects.filter(is_active=True).select_related('user').first()
    return render(request, 'expenses/form.html', {
        'departments': departments,
        'profile': profile,
        'action': 'create',
        'today_date': today_date,
        'second_approver': second_approver,
        'treasurer': treasurer,
        'budget_options': budget_options,
    })


@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)

    if expense.submitted_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to edit this form.')
        return redirect('expenses:dashboard')

    if not expense.can_edit():
        messages.error(request, 'This form cannot be edited after submission.')
        return redirect('expenses:detail', pk=pk)

    departments = Department.objects.filter(is_active=True)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    # Ensure the user's department still exists
    if profile.department_id:
        if not Department.objects.filter(id=profile.department_id).exists():
            profile.department_id = None
            profile.save()

    # Get budget options for the expense's department
    budget_options = build_budget_options_for_department(expense.department)

    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            phone = request.POST.get('phone_number', '').strip()
            dept_id = request.POST.get('department')
            request_date = request.POST.get('date')
            reason = request.POST.get('reason', '').strip()
            budget_choice = normalize_budget_choice(request.POST.get('budget_choice', ''))
            descriptions = request.POST.getlist('item_description[]')
            amounts = request.POST.getlist('item_amount[]')

            if not all([first_name, last_name, phone, dept_id, request_date, reason, budget_choice]):
                messages.error(request, 'Please fill all required fields.')
                return render(request, 'expenses/form.html', {
                    'departments': departments, 'expense': expense, 'profile': profile, 'action': 'edit', 'today_date': date.today().isoformat(),
                    'budget_options': budget_options,
                })

            dept = expense.department  # Department is fixed for edit

            # Validate budget choice
            allowed_budgets = [opt['value'] for opt in budget_options]
            if budget_choice not in allowed_budgets:
                messages.error(request, 'Invalid budget choice for this department.')
                return render(request, 'expenses/form.html', {
                    'departments': departments, 'expense': expense, 'profile': profile, 'action': 'edit', 'today_date': date.today().isoformat(),
                    'budget_options': budget_options,
                })

            total = 0
            items_data = []
            for i, (desc, amt) in enumerate(zip(descriptions, amounts)):
                desc = desc.strip()
                if desc:
                    try:
                        amt_val = float(amt) if amt else 0
                        if amt_val < 0:
                            messages.error(request, 'Item amounts cannot be negative.')
                            return redirect(request.path)
                        total += amt_val
                        items_data.append((desc, amt_val, i))
                    except ValueError:
                        messages.error(request, 'Invalid amount value. Please enter a valid number.')
                        return redirect(request.path)

            # Validate budget choice and balance
            if budget_choice != 'mk':
                selected_budget_label = next((opt['label'] for opt in budget_options if opt['value'] == budget_choice), budget_choice.replace('_', ' ').title())
                budget = Budget.objects.filter(department=dept).first()
                if not budget:
                    messages.error(request, 'No budget configured for this department.')
                    return render(request, 'expenses/form.html', {
                        'departments': departments, 'expense': expense, 'profile': profile, 'action': 'edit', 'today_date': date.today().isoformat(),
                        'budget_options': budget_options,
                    })

                if budget_choice == 'church_budget':
                    available = budget.church_budget
                elif budget_choice == 'contribution1':
                    available = budget.contribution1_amount
                elif budget_choice == 'contribution2':
                    available = budget.contribution2_amount
                else:
                    available = 0
                
                used_amount = ExpenseRequest.objects.filter(
                    department=dept,
                    budget_choice=budget_choice,
                    status__in=['approved', 'paid']
                ).exclude(pk=expense.pk).aggregate(total=models.Sum('total_amount'))['total'] or 0
                
                if total > (available - used_amount):
                    messages.error(request, f'Insufficient balance in {selected_budget_label}. Available: TZS {available - used_amount:,.0f}, Requested: TZS {total:,.0f}')
                    return render(request, 'expenses/form.html', {
                        'departments': departments, 'expense': expense, 'profile': profile, 'action': 'edit', 'today_date': date.today().isoformat(),
                        'budget_options': budget_options,
                    })

            with transaction.atomic():
                expense.first_name = first_name
                expense.last_name = last_name
                expense.phone_number = phone
                expense.department = dept
                expense.date = request_date
                expense.reason = reason
                expense.budget_choice = budget_choice
                expense.total_amount = total
                expense.save()
                expense.items.all().delete()
                for desc, amt, order in items_data:
                    ExpenseItem.objects.create(
                        expense_request=expense, description=desc, amount=amt, order=order
                    )

            messages.success(request, 'Expense request updated.')
            return redirect('expenses:detail', pk=expense.pk)
        except Exception as e:
            logger.error(f"Unexpected error in edit_expense POST: {e}\n{traceback.format_exc()}")
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return render(request, 'expenses/form.html', {
                'departments': departments, 'expense': expense, 'profile': profile, 'action': 'edit',
                'today_date': date.today().isoformat(), 'budget_options': budget_options,
            })

    second_approver = Approver.objects.filter(level='second', is_active=True).select_related('user').first()
    treasurer = Treasurer.objects.filter(is_active=True).select_related('user').first()
    return render(request, 'expenses/form.html', {
        'departments': departments, 'expense': expense, 'profile': profile, 'action': 'edit',
        'today_date': date.today().isoformat(), 'second_approver': second_approver, 'treasurer': treasurer,
        'budget_options': budget_options,
    })


@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    if expense.submitted_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('expenses:dashboard')
    if not expense.can_edit():
        messages.error(request, 'Cannot delete after submission.')
        return redirect('expenses:detail', pk=pk)
    expense.delete()
    messages.success(request, 'Expense request deleted.')
    return redirect('expenses:dashboard')


@login_required
def submit_expense(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    if expense.submitted_by != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('expenses:dashboard')
    if expense.status not in ['draft', 'rejected_for_editing']:
        messages.error(request, 'This form has already been submitted.')
        return redirect('expenses:detail', pk=pk)

    # Validate budget choice and balance before submitting
    if expense.budget_choice != 'mk':
        budget = Budget.objects.filter(department=expense.department).first()
        if not budget:
            messages.error(request, 'No budget configured for this department.')
            return redirect('expenses:detail', pk=pk)

        if expense.budget_choice == 'church_budget':
            available = budget.church_budget
        elif expense.budget_choice == 'contribution1':
            available = budget.contribution1_amount
        elif expense.budget_choice == 'contribution2':
            available = budget.contribution2_amount
        else:
            available = 0
        
        used_amount = ExpenseRequest.objects.filter(
            department=expense.department,
            budget_choice=expense.budget_choice,
            status__in=['approved', 'paid']
        ).exclude(pk=expense.pk).aggregate(total=models.Sum('total_amount'))['total'] or 0
        
        if expense.total_amount > (available - used_amount):
            budget_options = build_budget_options_for_department(expense.department)
            selected_budget_label = next((opt['label'] for opt in budget_options if opt['value'] == expense.budget_choice), expense.budget_choice.replace('_', ' ').title())
            messages.error(request, f'Insufficient balance in {selected_budget_label}. Please edit the form and choose a different budget or reduce the amount.')
            return redirect('expenses:detail', pk=pk)

    expense.status = 'submitted'
    expense.submitted_at = timezone.now()
    expense.rejection_reason = ''
    expense.save()

    # Notify first approvers for this department
    first_approvers = Approver.objects.filter(
        departments=expense.department, level='first', is_active=True
    ).select_related('user')
    for approver in first_approvers:
        send_notification(
            approver.user,
            f'New Expense Request: {expense.form_number}',
            f'{expense.first_name} {expense.last_name} submitted an expense request for {expense.department}.',
            f'/expenses/{expense.pk}/',
            'pending_expense'
        )

    messages.success(request, 'Expense request submitted successfully.')
    return redirect('expenses:detail', pk=pk)


@login_required
def expense_detail(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if not is_admin and not is_approver and not is_treasurer and expense.submitted_by != user:
        messages.error(request, 'Permission denied.')
        return redirect('expenses:dashboard')

    can_first_approve = False
    can_second_approve = False
    can_admin_approve = False
    can_mark_paid = False
    can_simple_reject = False
    can_see_rejection_type = False

    if is_approver:
        approver = user.approver_profile
        if approver.level == 'first':
            if not is_admin and not is_treasurer:
                can_see_rejection_type = True  # Only non-admin first approvers can see rejection type
            if expense.status == 'submitted':
                if expense.department in approver.departments.all():
                    can_first_approve = True
        elif approver.level == 'second' and expense.status == 'first_approved':
            can_second_approve = True
            can_simple_reject = True  # Second approvers can reject with comment only

    if is_admin and expense.status == 'second_approved':
        can_admin_approve = True
        can_simple_reject = True  # Admin can reject with comment only

    is_treasurer = hasattr(user, 'treasurer_profile')
    if is_treasurer and expense.status == 'second_approved':
        can_admin_approve = True  # Treasurers can also do final approval
        can_simple_reject = True  # Treasurers can reject with comment only

    if expense.status == 'approved' and not expense.is_paid and (is_admin or is_treasurer):
        can_mark_paid = True

    try:
        return render(request, 'expenses/detail.html', {
            'expense': expense,
            'is_approver': is_approver,
            'is_admin': is_admin,
            'is_treasurer': is_treasurer,
            'can_first_approve': can_first_approve,
            'can_second_approve': can_second_approve,
            'can_admin_approve': can_admin_approve,
            'can_mark_paid': can_mark_paid,
            'can_simple_reject': can_simple_reject,
            'can_see_rejection_type': can_see_rejection_type,
        })
    except Exception as e:
        logger.exception("Error rendering expense_detail for pk=%s", pk)
        return HttpResponse("Internal server error.", status=500)


@login_required
def approve_expense(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    user = request.user
    action = request.POST.get('action', 'approve')
    rejection_reason = request.POST.get('rejection_reason', '')
    reject_type = request.POST.get('reject_type', 'total')  # 'for_editing' or 'total'

    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if action == 'reject':
        if reject_type == 'for_editing':
            # Reject for editing - allow resubmission
            expense.status = 'rejected_for_editing'
            expense.rejection_reason = rejection_reason
            expense.save()
            send_notification(
                expense.submitted_by,
                f'Expense Request {expense.form_number} Needs Editing',
                f'Your expense request needs some changes. Reason: {rejection_reason}\n\nPlease make the necessary changes and resubmit.',
                f'/expenses/{expense.pk}/',
                'rejected_expense'
            )
            messages.success(request, 'Request returned for editing.')
        else:
            # Total rejection - permanent
            expense.status = 'rejected'
            expense.rejection_reason = rejection_reason
            expense.save()
            send_notification(
                expense.submitted_by,
                f'Expense Request {expense.form_number} Rejected',
                f'Your expense request has been rejected. Reason: {rejection_reason}',
                f'/expenses/{expense.pk}/',
                'rejected_expense'
            )
            messages.success(request, 'Request rejected.')
        return redirect('expenses:detail', pk=pk)

    if action == 'mark_paid':
        if expense.status == 'approved' and not expense.is_paid and (is_admin or is_treasurer):
            expense.is_paid = True
            expense.paid_at = timezone.now()
            expense.paid_by = user
            expense.status = 'paid'  # Update status to paid
            expense.save()
            send_notification(
                expense.submitted_by,
                f'Expense Request {expense.form_number} Paid',
                f'Your expense request has been marked as paid.',
                f'/expenses/{expense.pk}/',
                'paid_expense'
            )
            messages.success(request, 'Request marked as paid.')
        else:
            messages.error(request, 'You do not have permission to mark this as paid.')
        return redirect('expenses:detail', pk=pk)

    if is_approver:
        approver = user.approver_profile
        if approver.level == 'first' and expense.status == 'submitted':
            expense.status = 'first_approved'
            expense.first_approver = user
            expense.first_approver_name = user.get_full_name()
            expense.first_approver_phone = approver.phone_number
            expense.first_approved_at = timezone.now()
            expense.save()
            # Notify second approvers
            second_approvers = Approver.objects.filter(level='second', is_active=True).select_related('user')
            for sa in second_approvers:
                send_notification(
                    sa.user,
                    f'Expense Request Ready for 2nd Approval: {expense.form_number}',
                    f'Expense request from {expense.first_name} {expense.last_name} has been first-approved.',
                    f'/expenses/{expense.pk}/',
                    'pending_expense'
                )
            messages.success(request, 'First approval granted.')
        elif approver.level == 'second' and expense.status == 'first_approved':
            expense.status = 'second_approved'
            expense.second_approver = user
            expense.second_approver_name = user.get_full_name()
            expense.second_approver_phone = approver.phone_number
            expense.second_approved_at = timezone.now()
            expense.save()
            # Notify admins and treasurers
            admins = User.objects.filter(is_staff=True, is_active=True)
            treasurers = Treasurer.objects.filter(is_active=True).select_related('user')
            for admin in admins:
                send_notification(
                    admin,
                    f'Expense Request Ready for Final Approval: {expense.form_number}',
                    f'Expense request from {expense.first_name} {expense.last_name} awaits final approval.',
                    f'/expenses/{expense.pk}/',
                    'pending_expense'
                )
            for treasurer in treasurers:
                send_notification(
                    treasurer.user,
                    f'Expense Request Ready for Final Approval: {expense.form_number}',
                    f'Expense request from {expense.first_name} {expense.last_name} awaits final approval.',
                    f'/expenses/{expense.pk}/',
                    'pending_expense'
                )
            messages.success(request, 'Second approval granted.')
    elif is_admin and expense.status == 'second_approved':
        expense.status = 'approved'
        expense.admin_approver = user
        expense.admin_approved_at = timezone.now()
        expense.save()
        send_notification(
            expense.submitted_by,
            f'Expense Request {expense.form_number} Approved',
            f'Your expense request has been fully approved.',
            f'/expenses/{expense.pk}/',
            'approved_expense'
        )
        messages.success(request, 'Final approval granted.')
    elif is_treasurer and expense.status == 'second_approved':
        expense.status = 'approved'
        expense.treasurer_name = user.get_full_name()
        expense.treasurer_phone = user.treasurer_profile.phone_number
        expense.treasurer_approved_at = timezone.now()
        expense.save()
        send_notification(
            expense.submitted_by,
            f'Expense Request {expense.form_number} Approved',
            f'Your expense request has been fully approved.',
            f'/expenses/{expense.pk}/',
            'approved_expense'
        )
        messages.success(request, 'Final approval granted by Treasurer.')

    return redirect('expenses:detail', pk=pk)


@login_required
def update_payment(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    user = request.user
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if not (is_admin or is_treasurer) or expense.status != 'approved':
        messages.error(request, 'Permission denied.')
        return redirect('expenses:detail', pk=pk)

    if request.method == 'POST':
        payment_date = request.POST.get('payment_date')

        if not payment_date:
            messages.error(request, 'Payment date is required.')
            return redirect('expenses:detail', pk=pk)

        # Mark as paid with the provided payment date
        if not expense.is_paid:
            expense.is_paid = True
            expense.payment_date = payment_date
            expense.paid_at = timezone.now()
            expense.paid_by = user
            expense.status = 'paid'
            expense.save()
            
            send_notification(
                expense.submitted_by,
                f'Expense Request {expense.form_number} Paid',
                f'Your expense request has been marked as paid on {payment_date}.',
                f'/expenses/{expense.pk}/',
                'paid_expense'
            )
            messages.success(request, 'Request marked as paid.')
        else:
            messages.info(request, 'This request has already been marked as paid.')

    return redirect('expenses:detail', pk=pk)


@login_required
def download_expense_pdf(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if not is_admin and not is_approver and not is_treasurer and expense.submitted_by != user:
        messages.error(request, 'Permission denied.')
        return redirect('expenses:dashboard')

    # Generate expense PDF using ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    # Try to add church logo if it exists
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'clean_logo.png')
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=40*mm, height=40*mm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 3*mm))
        except:
            pass

    # Header
    header_style = ParagraphStyle('header', parent=styles['Normal'], fontSize=16,
                                   fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=6)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'], fontSize=12,
                                fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=6)
    normal_c = ParagraphStyle('nc', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=6)

    story.append(Paragraph("SEVENTH-DAY ADVENTIST CHURCH", header_style))
    story.append(Paragraph("EAST-COASTAL TANZANIA FIELD", sub_style))
    story.append(Paragraph("PO BOX 105, Bagamoyo", ParagraphStyle('po', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=8)))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("HATI YA MAOMBI YA FEDHA", ParagraphStyle('title', parent=styles['Normal'],
                            fontSize=13, fontName='Helvetica-Bold', alignment=TA_CENTER,
                            textColor=colors.HexColor('#003366'), spaceAfter=4)))
    story.append(Spacer(1, 4*mm))

    final_approval_date = 'N/A'
    if expense.admin_approved_at:
        final_approval_date = expense.admin_approved_at.strftime('%d %b %Y')
    elif expense.treasurer_approved_at:
        final_approval_date = expense.treasurer_approved_at.strftime('%d %b %Y')

    # Form number and date
    info_data = [
        ['Mtaa', 'Makongo Juu'],
        ['PO Box', '33516'],
        ['Kanisa', 'Makongo Juu SDA Church'],
        [f'Form No: {expense.form_number}', f'Tarehe: {expense.date}'],
        [f'Idara/Kitengo: {expense.department}', f'Namba ya Simu: {expense.phone_number}'],
        [f'Jina la Mkuu wa Idara/Kitengo: {expense.first_name} {expense.last_name}', f'Status: {expense.get_status_display()}'],
        ['Tarehe ya Kuidhinisha', final_approval_date],
    ]
    info_table = Table(info_data, colWidths=[90*mm, 80*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(f"<b>DHUMUNI LA MAOMBI YA FEDHA:</b> {expense.reason}", styles['Normal']))
    story.append(Spacer(1, 4*mm))

    # Items table
    items_header = [['#', 'Mchanganuo', 'Kiasi (TZS)']]
    items_rows = [[str(i+1), item.description, f"{item.amount:,.2f}"]
                  for i, item in enumerate(expense.items.all())]
    items_rows.append(['', 'JUMLA', f"{expense.total_amount:,.2f}"])

    items_table = Table(items_header + items_rows, colWidths=[15*mm, 120*mm, 35*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 8*mm))

    first_approver_name = expense.first_approver_name or (expense.first_approver.get_full_name() if expense.first_approver else 'Pending approval')
    second_approver_name = expense.second_approver_name or (expense.second_approver.get_full_name() if expense.second_approver else 'Pending approval')
    requester_name = f"{expense.first_name} {expense.last_name}"

    # Approval section
    story.append(Paragraph("<b>UTHIBITISHO/IDHINI YA MAOMBI YA FEDHA</b>", ParagraphStyle('ah', parent=styles['Normal'],
                            fontSize=11, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)))

    approval_data = [
        ['Mkuu wa Idara', 'Mzee wa Idara', 'Mzee Kiongozi', 'Mhazini'],
        [requester_name, first_approver_name, second_approver_name, expense.treasurer_name or "Pending"],
        ['Sahihi: _______________', 'Sahihi: _______________', 'Sahihi: _______________', 'Sahihi: _______________'],
        ['Tarehe: __________', 'Tarehe: __________', 'Tarehe: __________', 'Tarehe: __________'],
    ]
    approval_table = Table(approval_data, colWidths=[42*mm, 42*mm, 42*mm, 42*mm])
    approval_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
        ('ALIGN', (0, 2), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, 1), 0.5, colors.grey),
        ('LINEBELOW', (0, 1), (-1, 1), 0.5, colors.grey),
    ]))
    story.append(approval_table)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="expense_request_{expense.form_number}.pdf"'
    return response


@login_required
def download_payment_pdf(request, pk):
    expense = get_object_or_404(ExpenseRequest, pk=pk)
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if not is_admin and not is_treasurer and expense.submitted_by != user:
        messages.error(request, 'Permission denied.')
        return redirect('expenses:dashboard')

    if not expense.is_paid:
        messages.error(request, 'Payment form is available only after the request is marked as paid.')
        return redirect('expenses:detail', pk=pk)

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'clean_logo.png')
    pdf_buffer = payment_voucher_pdf(expense, logo_path)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payment_voucher_{expense.form_number}.pdf"'
    return response

