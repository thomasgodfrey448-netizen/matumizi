from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from expenses.models import ExpenseRequest
from retirement.models import RetirementForm
from core.models import Department
import io
import calendar
from django.utils import timezone
from datetime import date


@login_required
def reports_dashboard(request):
    # Redirect to expenses report by default
    return redirect('reports:expenses')


@login_required
def expenses_report(request):
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    # Filters
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    department_id = request.GET.get('department', '')
    payment_filter = request.GET.get('payment', '').strip()

    # Set default date range to current month only when no filters are applied.
    today = timezone.localdate()
    if not request.GET:
        date_from = today.replace(day=1).isoformat()
        date_to = today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat()

    if is_admin or is_treasurer:
        # Admins and Treasurers see all records
        qs = ExpenseRequest.objects.all().select_related('submitted_by', 'department')
    elif is_approver:
        approver = user.approver_profile
        if approver.level == 'first':
            # First approvers see only records from their assigned departments
            qs = ExpenseRequest.objects.filter(
                department__in=approver.departments.all()
            ).select_related('submitted_by', 'department')
        else:
            # Second approvers see all records
            qs = ExpenseRequest.objects.all().select_related('submitted_by', 'department')
    else:
        qs = ExpenseRequest.objects.filter(submitted_by=user).select_related('department')

    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    if search:
        qs = qs.filter(
            reason__icontains=search
        ) | qs.filter(first_name__icontains=search) | qs.filter(form_number__icontains=search)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if payment_filter == 'paid':
        qs = qs.filter(is_paid=True)
    elif payment_filter == 'unpaid':
        qs = qs.filter(is_paid=False)
    if department_id and (is_admin or is_treasurer):
        qs = qs.filter(department_id=department_id)

    # Evaluate queryset and calculate totals
    expenses_list = list(qs)
    total = sum(e.total_amount for e in expenses_list)
    approved_count = sum(1 for e in expenses_list if e.status in ['approved', 'paid'])
    pending_count = len(expenses_list) - approved_count

    return render(request, 'reports/expenses.html', {
        'expenses': expenses_list,
        'total': total,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'status_filter': status_filter,
        'department_id': department_id,
        'payment_filter': payment_filter,
        'is_admin': is_admin,
        'is_approver': is_approver,
        'is_treasurer': is_treasurer,
        'status_choices': [choice for choice in ExpenseRequest.STATUS_CHOICES if choice[0] != 'paid'],
        'departments': Department.objects.all().order_by('name'),
    })


@login_required
def retirement_report(request):
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    # Filters
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    department_id = request.GET.get('department', '')

    # Set default date range to current month only when no filters are applied.
    today = timezone.localdate()
    if not request.GET:
        date_from = today.replace(day=1).isoformat()
        date_to = today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat()

    if is_admin or is_treasurer:
        # Admins and Treasurers see all records
        qs = RetirementForm.objects.all().select_related('submitted_by', 'department')
    elif is_approver:
        approver = user.approver_profile
        if approver.level == 'first':
            # First approvers see only records from their assigned departments
            qs = RetirementForm.objects.filter(
                department__in=approver.departments.all()
            ).select_related('submitted_by', 'department')
        else:
            # Second approvers see all records
            qs = RetirementForm.objects.all().select_related('submitted_by', 'department')
    else:
        qs = RetirementForm.objects.filter(submitted_by=user).select_related('department')

    if date_from:
        qs = qs.filter(date_of_request__gte=date_from)
    if date_to:
        qs = qs.filter(date_of_request__lte=date_to)
    if search:
        qs = qs.filter(
            reason__icontains=search
        ) | qs.filter(first_name__icontains=search) | qs.filter(form_number__icontains=search)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if department_id and (is_admin or is_treasurer):
        qs = qs.filter(department_id=department_id)

    # Evaluate queryset and calculate totals
    retirements_list = list(qs)
    total = sum(r.total_amount for r in retirements_list)
    approved_count = sum(1 for r in retirements_list if r.status in ('approved', 'paid'))
    pending_count = len(retirements_list) - approved_count

    return render(request, 'reports/retirement.html', {
        'retirements': retirements_list,
        'total': total,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'status_filter': status_filter,
        'department_id': department_id,
        'is_admin': is_admin,
        'is_approver': is_approver,
        'is_treasurer': is_treasurer,
        'status_choices': [choice for choice in RetirementForm.STATUS_CHOICES if choice[0] != 'paid'],
        'departments': Department.objects.all().order_by('name'),
    })


@login_required
def download_expense_report(request):
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    department_id = request.GET.get('department', '').strip()
    payment_filter = request.GET.get('payment', '').strip()

    today = timezone.localdate()
    if not request.GET:
        date_from = today.replace(day=1).isoformat()
        date_to = today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat()

    if is_admin or is_treasurer:
        # Admins and Treasurers see all records
        qs = ExpenseRequest.objects.all().select_related('submitted_by', 'department')
    elif is_approver:
        approver = user.approver_profile
        if approver.level == 'first':
            # First approvers see only records from their assigned departments
            qs = ExpenseRequest.objects.filter(
                department__in=approver.departments.all()
            ).select_related('submitted_by', 'department')
        else:
            # Second approvers see all records
            qs = ExpenseRequest.objects.all().select_related('submitted_by', 'department')
    else:
        qs = ExpenseRequest.objects.filter(submitted_by=user).select_related('department')

    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    if search:
        qs = qs.filter(reason__icontains=search) | qs.filter(first_name__icontains=search) | qs.filter(form_number__icontains=search)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if payment_filter == 'paid':
        qs = qs.filter(is_paid=True)
    elif payment_filter == 'unpaid':
        qs = qs.filter(is_paid=False)
    if department_id and (is_admin or is_approver or is_treasurer):
        qs = qs.filter(department_id=department_id)

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("MAKONGO JUU SDA CHURCH - FINANCE DEPARTMENT",
                            ParagraphStyle('h', parent=styles['Normal'], fontSize=14,
                                           fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph("EXPENSE REQUESTS REPORT",
                            ParagraphStyle('t', parent=styles['Normal'], fontSize=12,
                                           fontName='Helvetica-Bold', alignment=TA_CENTER,
                                           textColor=colors.HexColor('#003366'), spaceAfter=8)))

    if date_from or date_to:
        period = f"Period: {date_from or 'All'} to {date_to or 'All'}"
        story.append(Paragraph(period, ParagraphStyle('p', parent=styles['Normal'],
                                fontSize=10, alignment=TA_CENTER, spaceAfter=8)))

    headers = [['#', 'Form No', 'Name', 'Department', 'Date', 'Reason', 'Amount (TZS)', 'Status', 'Paid']]
    rows = []
    total = 0
    for i, e in enumerate(qs):
        rows.append([
            str(i+1), e.form_number,
            f"{e.first_name} {e.last_name}",
            str(e.department or ''),
            str(e.date), e.reason[:40],
            f"{e.total_amount:,.2f}",
            e.get_status_display(),
            'Yes' if e.is_paid else 'No',
        ])
        total += e.total_amount
    rows.append(['', '', '', '', '', 'TOTAL', f"{total:,.2f}", '', ''])

    col_widths = [10*mm, 30*mm, 40*mm, 35*mm, 22*mm, 45*mm, 30*mm, 25*mm, 15*mm]
    table = Table(headers + rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (6, 0), (6, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="expense_report.pdf"'
    return response


@login_required
def download_retirement_report(request):
    user = request.user
    is_approver = hasattr(user, 'approver_profile')
    is_admin = user.is_staff or user.is_superuser
    is_treasurer = hasattr(user, 'treasurer_profile')

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    department_id = request.GET.get('department', '').strip()

    today = timezone.localdate()
    if not request.GET:
        date_from = today.replace(day=1).isoformat()
        date_to = today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat()

    if is_admin or is_treasurer:
        # Admins and Treasurers see all records
        qs = RetirementForm.objects.all().select_related('submitted_by', 'department')
    elif is_approver:
        approver = user.approver_profile
        if approver.level == 'first':
            # First approvers see only records from their assigned departments
            qs = RetirementForm.objects.filter(
                department__in=approver.departments.all()
            ).select_related('submitted_by', 'department')
        else:
            # Second approvers see all records
            qs = RetirementForm.objects.all().select_related('submitted_by', 'department')
    else:
        qs = RetirementForm.objects.filter(submitted_by=user).select_related('department')

    if date_from:
        qs = qs.filter(date_of_request__gte=date_from)
    if date_to:
        qs = qs.filter(date_of_request__lte=date_to)
    if search:
        qs = qs.filter(reason__icontains=search) | qs.filter(first_name__icontains=search) | qs.filter(form_number__icontains=search)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if department_id and (is_admin or is_approver or is_treasurer):
        qs = qs.filter(department_id=department_id)

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=15*mm, bottomMargin=15*mm,
                            leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("MAKONGO JUU SDA CHURCH - FINANCE DEPARTMENT",
                            ParagraphStyle('h', parent=styles['Normal'], fontSize=14,
                                           fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)))
    story.append(Paragraph("RETIREMENT FORMS REPORT",
                            ParagraphStyle('t', parent=styles['Normal'], fontSize=12,
                                           fontName='Helvetica-Bold', alignment=TA_CENTER,
                                           textColor=colors.HexColor('#1a5276'), spaceAfter=8)))

    headers = [['#', 'Form No', 'Name', 'Department', 'Date Req.', 'Date Ret.', 'Remaining', 'Status']]
    rows = []
    total = 0
    for i, r in enumerate(qs):
        rows.append([
            str(i+1), r.form_number,
            f"{r.first_name} {r.last_name}",
            str(r.department or ''),
            str(r.date_of_request),
            str(r.date_of_retirement),
            f"{r.remaining_amount:,.2f}",
            r.get_status_display(),
        ])
        total += r.remaining_amount
    rows.append(['', '', '', '', '', 'TOTAL', f"{total:,.2f}", ''])

    col_widths = [10*mm, 28*mm, 35*mm, 30*mm, 20*mm, 20*mm, 28*mm, 22*mm]
    table = Table(headers + rows, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (6, 0), (7, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d6eaf8')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="retirement_report.pdf"'
    return response
