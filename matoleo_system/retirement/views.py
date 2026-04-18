from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.contrib.auth.models import User
from django.conf import settings
import os
import io
import calendar
import logging
from datetime import datetime, date
from .models import RetirementForm, RetirementItem
from core.models import Department, Approver, Treasurer, Notification, UserProfile
from core.pdf_utils import retirement_to_pdf, payment_voucher_pdf

logger = logging.getLogger(__name__)


def send_notification(recipient, title, message, link='', notification_type='general'):
    # Ensure link is absolute
    if link and not link.startswith('/'):
        link = '/' + link
    Notification.objects.create(recipient=recipient, title=title, message=message, link=link, notification_type=notification_type)


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
def retirement_dashboard(request):
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if is_admin or is_treasurer:
        # Admins and Treasurers see all records
        forms = RetirementForm.objects.all().select_related('submitted_by', 'department')
    elif is_approver:
        approver = user.approver_profile
        if approver.level == 'first':
            # First approvers see only records from their assigned departments
            forms = RetirementForm.objects.filter(
                department__in=approver.departments.all()
            ).select_related('submitted_by', 'department')
        else:
            # Second approvers see all records
            forms = RetirementForm.objects.all().select_related('submitted_by', 'department')
    else:
        forms = RetirementForm.objects.filter(submitted_by=user).select_related('department')

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

    forms = forms.filter(date_of_request__gte=start_date, date_of_request__lte=end_date)

    # Count pending and approved forms
    pending_forms = forms.exclude(status='approved').exclude(status='rejected')
    approved_forms = forms.filter(status='approved')

    return render(request, 'retirement/dashboard.html', {
        'forms': forms,
        'pending_count': pending_forms.count(),
        'approved_count': approved_forms.count(),
        'is_approver': is_approver,
        'is_admin': is_admin,
        'is_treasurer': is_treasurer,
        'selected_month': selected_month,
        'date_from': start_date,
        'date_to': end_date,
    })


@login_required
def create_retirement(request):
    if hasattr(request.user, 'approver_profile'):
        messages.error(request, 'Approvers cannot create retirement forms.')
        return redirect('retirement:dashboard')

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
        date_request = request.POST.get('date_of_request')
        date_retirement = request.POST.get('date_of_retirement')
        reason = request.POST.get('reason', '').strip()
        exp_request_form_no = request.POST.get('exp_request_form_no', '').strip()
        remaining = request.POST.get('remaining_amount', '0')
        attachment = request.FILES.get('attachment')
        descriptions = request.POST.getlist('item_description[]')
        amounts = request.POST.getlist('item_amount[]')

        if not all([first_name, last_name, phone, dept_id, date_request, date_retirement, reason]):
            messages.error(request, 'Please fill all required fields.')
            return render(request, 'retirement/form.html', {
                'departments': departments,
                'profile': profile,
                'action': 'create',
                'today_date': date.today().isoformat(),
            })

        # Validate dates
        try:
            from datetime import date as date_type
            parsed_request = datetime.strptime(date_request, '%Y-%m-%d').date()
            parsed_retirement = datetime.strptime(date_retirement, '%Y-%m-%d').date()
            if parsed_retirement < parsed_request:
                messages.error(request, 'Retirement date cannot be before the request date.')
                return render(request, 'retirement/form.html', {
                    'departments': departments,
                    'profile': profile,
                    'action': 'create',
                    'today_date': date.today().isoformat(),
                })
        except ValueError:
            messages.error(request, 'Invalid date format. Please use the date picker.')
            return render(request, 'retirement/form.html', {
                'departments': departments,
                'profile': profile,
                'action': 'create',
                'today_date': date.today().isoformat(),
            })

        # Validate file attachment
        if attachment:
            allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png'}
            max_size_mb = 5
            ext = os.path.splitext(attachment.name)[1].lower()
            if ext not in allowed_extensions:
                messages.error(request, 'Only PDF, JPG, and PNG files are allowed.')
                return render(request, 'retirement/form.html', {
                    'departments': departments,
                    'profile': profile,
                    'action': 'create',
                    'today_date': date.today().isoformat(),
                })
            if attachment.size > max_size_mb * 1024 * 1024:
                messages.error(request, f'File size must not exceed {max_size_mb}MB.')
                return render(request, 'retirement/form.html', {
                    'departments': departments,
                    'profile': profile,
                    'action': 'create',
                    'today_date': date.today().isoformat(),
                })

        try:
            dept = Department.objects.get(id=dept_id)
        except Department.DoesNotExist:
            messages.error(request, 'Invalid department.')
            return render(request, 'retirement/form.html', {
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
                    if amt_val < 0:
                        messages.error(request, 'Item amounts cannot be negative.')
                        return redirect(request.path)
                    total += amt_val
                    items_data.append((desc, amt_val, i))
                except ValueError:
                    messages.error(request, 'Invalid amount value. Please enter a valid number.')
                    return redirect(request.path)

        try:
            remaining_val = float(remaining)
        except ValueError:
            remaining_val = 0

        with transaction.atomic():
            form = RetirementForm.objects.create(
                submitted_by=request.user,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone,
                department=dept,
                date_of_request=date_request,
                date_of_retirement=date_retirement,
                reason=reason,
                exp_request_form_no=exp_request_form_no,
                total_amount=total,
                remaining_amount=remaining_val,
                attachment=attachment,
                status='draft',
            )
            for desc, amt, order in items_data:
                RetirementItem.objects.create(
                    retirement_form=form, description=desc, amount=amt, order=order
                )

        messages.success(request, f'Retirement form {form.form_number} created as draft.')
        return redirect('retirement:detail', pk=form.pk)

    today_date = date.today().isoformat()
    second_approver = Approver.objects.filter(level='second', is_active=True).select_related('user').first()
    treasurer = Treasurer.objects.filter(is_active=True).select_related('user').first()
    return render(request, 'retirement/form.html', {
        'departments': departments,
        'profile': profile,
        'action': 'create',
        'today_date': today_date,
        'second_approver': second_approver,
        'treasurer': treasurer,
    })


@login_required
def edit_retirement(request, pk):
    form = get_object_or_404(RetirementForm, pk=pk)
    if form.submitted_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('retirement:dashboard')
    if not form.can_edit():
        messages.error(request, 'Cannot edit after submission.')
        return redirect('retirement:detail', pk=pk)

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
        date_request = request.POST.get('date_of_request')
        date_retirement = request.POST.get('date_of_retirement')
        reason = request.POST.get('reason', '').strip()
        exp_request_form_no = request.POST.get('exp_request_form_no', '').strip()
        remaining = request.POST.get('remaining_amount', '0')
        attachment = request.FILES.get('attachment')
        descriptions = request.POST.getlist('item_description[]')
        amounts = request.POST.getlist('item_amount[]')

        try:
            dept = Department.objects.get(id=dept_id)
        except Department.DoesNotExist:
            messages.error(request, 'Invalid department.')
            return render(request, 'retirement/form.html', {
                'departments': departments, 'form_obj': form, 'profile': profile, 'action': 'edit'
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

        try:
            remaining_val = float(remaining)
        except ValueError:
            remaining_val = 0

        with transaction.atomic():
            form.first_name = first_name
            form.last_name = last_name
            form.phone_number = phone
            form.department = dept
            form.date_of_request = date_request
            form.date_of_retirement = date_retirement
            form.reason = reason
            form.exp_request_form_no = exp_request_form_no
            form.total_amount = total
            form.remaining_amount = remaining_val
            if attachment:
                form.attachment = attachment
            form.save()
            form.items.all().delete()
            for desc, amt, order in items_data:
                RetirementItem.objects.create(
                    retirement_form=form, description=desc, amount=amt, order=order
                )

        messages.success(request, 'Retirement form updated.')
        return redirect('retirement:detail', pk=form.pk)

    second_approver = Approver.objects.filter(level='second', is_active=True).select_related('user').first()
    treasurer = Treasurer.objects.filter(is_active=True).select_related('user').first()
    return render(request, 'retirement/form.html', {
        'departments': departments, 'form_obj': form, 'profile': profile, 'action': 'edit',
        'today_date': date.today().isoformat(), 'second_approver': second_approver, 'treasurer': treasurer,
    })


@login_required
def delete_retirement(request, pk):
    form = get_object_or_404(RetirementForm, pk=pk)
    if form.submitted_by != request.user and not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('retirement:dashboard')
    if not form.can_edit():
        messages.error(request, 'Cannot delete after submission.')
        return redirect('retirement:detail', pk=pk)
    form.delete()
    messages.success(request, 'Retirement form deleted.')
    return redirect('retirement:dashboard')


@login_required
def submit_retirement(request, pk):
    form = get_object_or_404(RetirementForm, pk=pk)
    if form.submitted_by != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('retirement:dashboard')
    if form.status not in ['draft', 'rejected_for_editing']:
        messages.error(request, 'Already submitted.')
        return redirect('retirement:detail', pk=pk)

    form.status = 'submitted'
    form.submitted_at = timezone.now()
    form.rejection_reason = ''
    form.save()

    first_approvers = Approver.objects.filter(
        departments=form.department, level='first', is_active=True
    ).select_related('user')
    for approver in first_approvers:
        send_notification(
            approver.user,
            f'New Retirement Form: {form.form_number}',
            f'{form.first_name} {form.last_name} submitted a retirement form.',
            f'/retirement/{form.pk}/',
            'pending_retirement'
        )

    messages.success(request, 'Retirement form submitted.')
    return redirect('retirement:detail', pk=pk)


@login_required
def retirement_detail(request, pk):
    form = get_object_or_404(RetirementForm, pk=pk)
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if not is_admin and not is_approver and not is_treasurer and form.submitted_by != user:
        messages.error(request, 'Permission denied.')
        return redirect('retirement:dashboard')

    can_first_approve = False
    can_second_approve = False
    can_admin_approve = False
    can_mark_paid = False
    can_simple_reject = False
    can_see_rejection_type = False

    if is_approver:
        approver = user.approver_profile
        if approver.level == 'first' and form.status == 'submitted':
            if form.department in approver.departments.all():
                can_first_approve = True
                if not is_admin and not is_treasurer:
                    can_see_rejection_type = True  # Only non-admin first approvers can see rejection type
        elif approver.level == 'second' and form.status == 'first_approved':
            can_second_approve = True
            can_simple_reject = True  # Second approvers can reject with comment only

    if is_admin and form.status == 'second_approved':
        can_admin_approve = True
        can_simple_reject = True  # Admin can reject with comment only

    is_treasurer = hasattr(user, 'treasurer_profile')
    if is_treasurer and form.status == 'second_approved':
        can_admin_approve = True  # Treasurers can also do final approval
        can_simple_reject = True  # Treasurers can reject with comment only

    if form.status == 'approved' and not form.is_paid and (is_admin or is_treasurer):
        can_mark_paid = True

    try:
        return render(request, 'retirement/detail.html', {
            'form': form,
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
        logger.exception("Error rendering retirement_detail for pk=%s", pk)
        return HttpResponse("Internal server error.", status=500)


@login_required
def approve_retirement(request, pk):
    form = get_object_or_404(RetirementForm, pk=pk)
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
            form.status = 'rejected_for_editing'
            form.rejection_reason = rejection_reason
            form.save()
            send_notification(
                form.submitted_by,
                f'Retirement Form {form.form_number} Needs Editing',
                f'Your retirement form needs some changes. Reason: {rejection_reason}\n\nPlease make the necessary changes and resubmit.',
                f'/retirement/{form.pk}/',
                'rejected_retirement'
            )
            messages.success(request, 'Form returned for editing.')
        else:
            # Total rejection - permanent
            form.status = 'rejected'
            form.rejection_reason = rejection_reason
            form.save()
            send_notification(
                form.submitted_by,
                f'Retirement Form {form.form_number} Rejected',
                f'Your retirement form has been rejected. Reason: {rejection_reason}',
                f'/retirement/{form.pk}/',
                'rejected_retirement'
            )
            messages.success(request, 'Form rejected.')
        return redirect('retirement:detail', pk=pk)

    if action == 'mark_paid':
        if form.status == 'approved' and not form.is_paid and (is_admin or is_treasurer):
            form.is_paid = True
            form.paid_at = timezone.now()
            form.paid_by = user
            form.status = 'paid'  # Update status to paid
            form.save()
            send_notification(
                form.submitted_by,
                f'Retirement Form {form.form_number} Paid',
                f'Your retirement form has been marked as paid.',
                f'/retirement/{form.pk}/',
                'paid_retirement'
            )
            messages.success(request, 'Form marked as paid.')
        else:
            messages.error(request, 'You do not have permission to mark this as paid.')
        return redirect('retirement:detail', pk=pk)

    if is_approver:
        approver = user.approver_profile
        if approver.level == 'first' and form.status == 'submitted':
            form.status = 'first_approved'
            form.first_approver = user
            form.first_approver_name = user.get_full_name()
            form.first_approver_phone = approver.phone_number
            form.first_approved_at = timezone.now()
            form.save()
            second_approvers = Approver.objects.filter(level='second', is_active=True).select_related('user')
            for sa in second_approvers:
                send_notification(
                    sa.user,
                    f'Retirement Form Ready for 2nd Approval: {form.form_number}',
                    f'Retirement form from {form.first_name} {form.last_name} has been first-approved.',
                    f'/retirement/{form.pk}/',
                    'pending_retirement'
                )
            messages.success(request, 'First approval granted.')
        elif approver.level == 'second' and form.status == 'first_approved':
            form.status = 'second_approved'
            form.second_approver = user
            form.second_approver_name = user.get_full_name()
            form.second_approver_phone = approver.phone_number
            form.second_approved_at = timezone.now()
            form.save()
            admins = User.objects.filter(is_staff=True, is_active=True)
            treasurers = Treasurer.objects.filter(is_active=True).select_related('user')
            for admin in admins:
                send_notification(
                    admin,
                    f'Retirement Form Ready for Final Approval: {form.form_number}',
                    f'Retirement form from {form.first_name} {form.last_name} awaits final approval.',
                    f'/retirement/{form.pk}/',
                    'pending_retirement'
                )
            for treasurer in treasurers:
                send_notification(
                    treasurer.user,
                    f'Retirement Form Ready for Final Approval: {form.form_number}',
                    f'Retirement form from {form.first_name} {form.last_name} awaits final approval.',
                    f'/retirement/{form.pk}/',
                    'pending_retirement'
                )
            messages.success(request, 'Second approval granted.')
    elif is_admin and form.status == 'second_approved':
        form.status = 'approved'
        form.admin_approver = user
        form.admin_approved_at = timezone.now()
        form.save()
        send_notification(
            form.submitted_by,
            f'Retirement Form {form.form_number} Approved',
            f'Your retirement form has been fully approved.',
            f'/retirement/{form.pk}/',
            'approved_retirement'
        )
        messages.success(request, 'Final approval granted.')
    elif is_treasurer and form.status == 'second_approved':
        form.status = 'approved'
        form.treasurer_name = user.get_full_name()
        form.treasurer_phone = user.treasurer_profile.phone_number
        form.treasurer_approved_at = timezone.now()
        form.save()
        send_notification(
            form.submitted_by,
            f'Retirement Form {form.form_number} Approved',
            f'Your retirement form has been fully approved.',
            f'/retirement/{form.pk}/',
            'approved_retirement'
        )
        messages.success(request, 'Final approval granted by Treasurer.')

    return redirect('retirement:detail', pk=pk)


@login_required
def update_payment_retirement(request, pk):
    form = get_object_or_404(RetirementForm, pk=pk)
    user = request.user
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if not (is_admin or is_treasurer) or form.status != 'approved':
        messages.error(request, 'Permission denied.')
        return redirect('retirement:detail', pk=pk)

    if request.method == 'POST':
        payment_date = request.POST.get('payment_date')

        if not payment_date:
            messages.error(request, 'Payment date is required.')
            return redirect('retirement:detail', pk=pk)

        # Mark as paid with the provided payment date
        if not form.is_paid:
            form.is_paid = True
            form.payment_date = payment_date
            form.paid_at = timezone.now()
            form.paid_by = user
            form.status = 'paid'
            form.save()
            
            # Send notification to submitter
            send_notification(
                form.submitted_by,
                f'Retirement Form {form.form_number} Paid',
                f'Your retirement form has been marked as paid on {payment_date}.',
                f'/retirement/{form.pk}/',
                'paid_retirement'
            )
            messages.success(request, 'Request marked as paid.')
        else:
            messages.info(request, 'This request has already been marked as paid.')

    return redirect('retirement:detail', pk=pk)


@login_required
def download_retirement_pdf(request, pk):
    form = get_object_or_404(RetirementForm, pk=pk)
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if not is_admin and not is_approver and not is_treasurer and form.submitted_by != user:
        messages.error(request, 'Permission denied.')
        return redirect('retirement:dashboard')

    # If paid, download payment voucher
    if form.is_paid:
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo_clean_plain_v2.png')
        pdf_buffer = payment_voucher_pdf(form, logo_path)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="payment_voucher_{form.form_number}.pdf"'
        return response

    # Generate retirement PDF using ReportLab
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    # Add the church logo from static files
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo_clean_plain_v2.png')
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=40*mm, height=40*mm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 3*mm))
        except:
            pass

    header_style = ParagraphStyle('header', parent=styles['Normal'], fontSize=16,
                                   fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=3)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'], fontSize=12,
                                fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=2)

    story.append(Paragraph("SEVENTH-DAY ADVENTIST CHURCH", header_style))
    story.append(Paragraph("EAST-COASTAL TANZANIA FIELD", sub_style))
    story.append(Paragraph("PO BOX 105", ParagraphStyle('po', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=1)))
    story.append(Paragraph("Bagamoyo", ParagraphStyle('mtaa', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=4)))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("HATI YA MAREJESHO YA FEDHA", ParagraphStyle('title', parent=styles['Normal'],
                            fontSize=13, fontName='Helvetica-Bold', alignment=TA_CENTER,
                            textColor=colors.HexColor('#003366'), spaceAfter=4)))
    story.append(Spacer(1, 4*mm))

    # Form details
    info_data = [
        ['Mtaa', 'Makongo Juu'],
        ['PO Box', '33516'],
        ['Kanisa', 'Makongo Juu SDA Church'],
        [f'Form No: {form.form_number}', f'Tarehe kuomba pesa: {form.date_of_request}'],
        [f'Idara/Kitengo: {form.department}', f'Namba ya Simu: {form.phone_number}'],
        [f'Jina la Mkuu wa Idara/Kitengo: {form.first_name} {form.last_name}', f'Status: {form.get_status_display()}'],
        [f'Tarehe ya Marejesho: {form.date_of_retirement}', ''],
    ]
    info_table = Table(info_data, colWidths=[90*mm, 80*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph(f"<b>MAELEZO YA MAREJESHO:</b> {form.reason}", styles['Normal']))
    story.append(Spacer(1, 4*mm))

    # Items table
    items_header = [['#', 'Mchanganuo', 'Kiasi (TZS)']]
    items_rows = [[str(i+1), item.description, f"{item.amount:,.2f}"]
                  for i, item in enumerate(form.items.all())]
    items_rows.append(['', 'JUMLA', f"{form.total_amount:,.2f}"])

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

    requester_title = ParagraphStyle('requester_title', parent=styles['Normal'], fontSize=12,
                                     fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'), spaceAfter=4)
    requester_value = ParagraphStyle('requester_value', parent=styles['Normal'], fontSize=10, leading=14)

    story.append(Paragraph('Mkuu wa Idara/Kitengo', requester_title))
    story.append(Paragraph(f'Jina: {form.first_name} {form.last_name}', requester_value))
    story.append(Paragraph('Sahihi: ________________________________', requester_value))
    story.append(Paragraph('Tarehe: ________________________________', requester_value))
    story.append(Spacer(1, 8*mm))

    treasurer_name = form.treasurer_name or '________________'
    treasurer_phone = form.treasurer_phone or '___________'

    story.append(Paragraph('Mhazini', requester_title))
    story.append(Paragraph(f'Jina: {treasurer_name}', requester_value))
    story.append(Paragraph('Sahihi: ________________________________', requester_value))
    story.append(Paragraph(f'Namba ya simu: {treasurer_phone}', requester_value))
    story.append(Paragraph('Tarehe: ________________________________', requester_value))

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="retirement_form_{form.form_number}.pdf"'
    return response


@login_required
def download_payment_pdf_retirement(request, pk):
    form = get_object_or_404(RetirementForm, pk=pk)
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    if not is_admin and not is_treasurer and form.submitted_by != user:
        messages.error(request, 'Permission denied.')
        return redirect('retirement:dashboard')

    if not form.is_paid:
        messages.error(request, 'Payment form is available only after the form is marked as paid.')
        return redirect('retirement:detail', pk=pk)

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo_clean_plain_v2.png')
    pdf_buffer = payment_voucher_pdf(form, logo_path)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="payment_voucher_{form.form_number}.pdf"'
    return response

