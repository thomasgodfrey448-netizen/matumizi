from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.contrib.auth.models import User
from .models import ExpenseRequest, ExpenseItem
import calendar
from datetime import datetime, date
from core.models import Department, Approver, Treasurer, Notification, UserProfile
from core.pdf_utils import expense_to_pdf, payment_voucher_pdf
from django.conf import settings
import io
import os


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

    # Count pending and approved requests
    pending_requests = requests.exclude(status='approved').exclude(status='rejected')
    approved_requests = requests.filter(status='approved')

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

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        dept_id = request.POST.get('department')
        request_date = request.POST.get('date')
        reason = request.POST.get('reason', '').strip()
        descriptions = request.POST.getlist('item_description[]')
        amounts = request.POST.getlist('item_amount[]')

        if not all([first_name, last_name, phone, dept_id, request_date, reason]):
            messages.error(request, 'Please fill all required fields.')
            return render(request, 'expenses/form.html', {
                'departments': departments,
                'profile': profile,
                'action': 'create',
                'today_date': date.today().isoformat(),
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
            })

        total = 0
        items_data = []
        for i, (desc, amt) in enumerate(zip(descriptions, amounts)):
            desc = desc.strip()
            if desc:
                try:
                    amt_val = float(amt) if amt else 0
                    total += amt_val
                    items_data.append((desc, amt_val, i))
                except ValueError:
                    pass

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
                status='draft',
            )
            for desc, amt, order in items_data:
                ExpenseItem.objects.create(
                    expense_request=expense,
                    description=desc,
                    amount=amt,
                    order=order,
                )

        messages.success(request, f'Expense request {expense.form_number} created as draft.')
        return redirect('expenses:detail', pk=expense.pk)

    today_date = date.today().isoformat()
    return render(request, 'expenses/form.html', {
        'departments': departments,
        'profile': profile,
        'action': 'create',
        'today_date': today_date,
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

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        dept_id = request.POST.get('department')
        request_date = request.POST.get('date')
        reason = request.POST.get('reason', '').strip()
        descriptions = request.POST.getlist('item_description[]')
        amounts = request.POST.getlist('item_amount[]')

        try:
            dept = Department.objects.get(id=dept_id)
        except Department.DoesNotExist:
            messages.error(request, 'Invalid department.')
            return render(request, 'expenses/form.html', {
                'departments': departments, 'expense': expense, 'profile': profile, 'action': 'edit', 'today_date': date.today().isoformat(),
            })

        total = 0
        items_data = []
        for i, (desc, amt) in enumerate(zip(descriptions, amounts)):
            desc = desc.strip()
            if desc:
                try:
                    amt_val = float(amt) if amt else 0
                    total += amt_val
                    items_data.append((desc, amt_val, i))
                except ValueError:
                    pass

        with transaction.atomic():
            expense.first_name = first_name
            expense.last_name = last_name
            expense.phone_number = phone
            expense.department = dept
            expense.date = request_date
            expense.reason = reason
            expense.total_amount = total
            expense.save()
            expense.items.all().delete()
            for desc, amt, order in items_data:
                ExpenseItem.objects.create(
                    expense_request=expense, description=desc, amount=amt, order=order
                )

        messages.success(request, 'Expense request updated.')
        return redirect('expenses:detail', pk=expense.pk)

    return render(request, 'expenses/form.html', {
        'departments': departments, 'expense': expense, 'profile': profile, 'action': 'edit', 'today_date': date.today().isoformat(),
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
        print(f"Error rendering expense_detail for pk={pk}: {e}")
        import traceback
        print(traceback.format_exc())
        return HttpResponse(f"Internal server error: {str(e)}", status=500)


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
        expense.treasurer_name = user.get_full_name()
        expense.treasurer_approved_at = timezone.now()
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
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
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
                                   fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=3)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'], fontSize=12,
                                fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=2)
    normal_c = ParagraphStyle('nc', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=2)

    story.append(Paragraph("SEVENTH-DAY ADVENTIST CHURCH", header_style))
    story.append(Paragraph("EAST-CENTRAL TANZANIA CONFERENCE", sub_style))
    story.append(Paragraph("PO BOX 105", ParagraphStyle('po', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=1)))
    story.append(Paragraph("Bagamoyo", ParagraphStyle('mtaa', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("EXPENSE REQUEST FORM", ParagraphStyle('title', parent=styles['Normal'],
                            fontSize=13, fontName='Helvetica-Bold', alignment=TA_CENTER,
                            textColor=colors.HexColor('#003366'), spaceAfter=4)))
    story.append(Spacer(1, 4*mm))

    # Form number and date
    info_data = [
        ['Mtaa', 'Makongo Juu'],
        ['PO Box', '33516'],
        ['Kanisa', 'Makongo Juu SDA Church'],
        [f'Form No: {expense.form_number}', f'Date: {expense.date}'],
        [f'Department: {expense.department}', f'Phone: {expense.phone_number}'],
        [f'Name: {expense.first_name} {expense.last_name}', f'Status: {expense.get_status_display()}'],
    ]
    info_table = Table(info_data, colWidths=[90*mm, 80*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(f"<b>Reason for Request:</b> {expense.reason}", styles['Normal']))
    story.append(Spacer(1, 4*mm))

    # Items table
    items_header = [['#', 'Description', 'Amount (TZS)']]
    items_rows = [[str(i+1), item.description, f"{item.amount:,.2f}"]
                  for i, item in enumerate(expense.items.all())]
    items_rows.append(['', 'TOTAL', f"{expense.total_amount:,.2f}"])

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
    story.append(Paragraph("<b>APPROVAL SIGNATURES</b>", ParagraphStyle('ah', parent=styles['Normal'],
                            fontSize=11, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)))

    approval_data = [
        ['Requester', 'First Approver', 'Second Approver'],
        [f'Name: {requester_name}', f'Name: {first_approver_name}', f'Name: {second_approver_name}'],
        ['Signature: _______________', 'Signature: _______________', 'Signature: _______________'],
        ['Date: __________________', 'Date: __________________', 'Date: __________________'],
    ]
    approval_table = Table(approval_data, colWidths=[57*mm, 57*mm, 57*mm])
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

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    pdf_buffer = payment_voucher_pdf(expense, logo_path)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payment_voucher_{expense.form_number}.pdf"'
    return response

