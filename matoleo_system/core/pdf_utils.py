from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from django.conf import settings


def generate_pdf_with_logo(filename, title, data_list, logo_path=None):
    """
    Generate PDF with church logo and form data
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Add logo if provided
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=1*inch, height=1*inch)
            logo_table = Table([[logo]], colWidths=[7.5*inch])
            logo_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
            elements.append(logo_table)
            elements.append(Spacer(1, 0.2*inch))
        except:
            pass
    
    # Add title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#003366'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Add data table
    table_data = data_list
    col_widths = [1.5*inch, 5.5*inch]
    
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F0F7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.4*inch))
    
    # Add signature section
    sig_style = ParagraphStyle(
        'SigStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
    )
    
    sig_data = [
        [Paragraph('_________________<br/>First Approver Signature', sig_style),
         Paragraph('_________________<br/>Second Approver Signature', sig_style),
         Paragraph('_________________<br/>Treasurer Signature', sig_style)],
    ]
    
    sig_table = Table(sig_data, colWidths=[2.3*inch, 2.3*inch, 2.3*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def expense_to_pdf(expense_request, logo_path=None):
    """
    Convert expense request to PDF
    """
    data = [
        ['Field', 'Value'],
        ['Employee Name', str(expense_request.user)],
        ['Department', str(expense_request.department)],
        ['Purpose', expense_request.purpose],
        ['Amount', f'${expense_request.amount}'],
        ['Date Submitted', str(expense_request.created_at.date())],
        ['Status', expense_request.get_status_display()],
        ['', ''],
        ['First Approver', expense_request.first_approver_name or 'TBD'],
        ['First Approver Phone', expense_request.first_approver_phone or 'TBD'],
        ['First Approver Approved', 'Yes' if expense_request.first_approver_approved else 'No'],
        ['', ''],
        ['Second Approver', expense_request.second_approver_name or 'TBD'],
        ['Second Approver Phone', expense_request.second_approver_phone or 'TBD'],
        ['Second Approver Approved', 'Yes' if expense_request.second_approver_approved else 'No'],
        ['', ''],
        ['Treasurer', expense_request.treasurer_name or 'TBD'],
        ['Treasurer Phone', expense_request.treasurer_phone or 'TBD'],
        ['Treasurer Approved', 'Yes' if hasattr(expense_request, 'treasurer_approved') and expense_request.treasurer_approved else 'No'],
    ]
    
    return generate_pdf_with_logo('expense_request.pdf', 'Expense Request Form', data, logo_path)


def retirement_to_pdf(retirement_form, logo_path=None):
    """
    Convert retirement form to PDF
    """
    data = [
        ['Field', 'Value'],
        ['Employee Name', str(retirement_form.user)],
        ['Department', str(retirement_form.department)],
        ['Service Years', str(retirement_form.years_of_service)],
        ['Date Submitted', str(retirement_form.created_at.date())],
        ['Status', retirement_form.get_status_display()],
        ['', ''],
        ['First Approver', retirement_form.first_approver_name or 'TBD'],
        ['First Approver Phone', retirement_form.first_approver_phone or 'TBD'],
        ['First Approver Approved', 'Yes' if retirement_form.first_approver_approved else 'No'],
        ['', ''],
        ['Second Approver', retirement_form.second_approver_name or 'TBD'],
        ['Second Approver Phone', retirement_form.second_approver_phone or 'TBD'],
        ['Second Approver Approved', 'Yes' if retirement_form.second_approver_approved else 'No'],
        ['', ''],
        ['Treasurer', retirement_form.treasurer_name or 'TBD'],
        ['Treasurer Phone', retirement_form.treasurer_phone or 'TBD'],
        ['Treasurer Approved', 'Yes' if hasattr(retirement_form, 'treasurer_approved') and retirement_form.treasurer_approved else 'No'],
    ]
    
    return generate_pdf_with_logo('retirement_form.pdf', 'Retirement Form', data, logo_path)


def payment_voucher_pdf(request_obj, logo_path=None):
    """
    Generate payment voucher PDF for expense or retirement with payment form layout.
    """
    payment_method = getattr(request_obj, 'payment_method', '') or 'N/A'
    reference_number = getattr(request_obj, 'reference_number', '') or 'N/A'
    
    # Determine if this is expense or retirement
    is_expense = hasattr(request_obj, 'reason')
    
    # Set default location info
    location_mtaa = 'Makongo Juu'
    location_pobox = '33516'
    kanisa = 'Makongo Juu SDA Church'

    if is_expense:  # ExpenseRequest
        request_date = request_obj.date.strftime('%Y-%m-%d') if request_obj.date else 'N/A'
        final_approval_date = request_obj.admin_approved_at.strftime('%Y-%m-%d') if request_obj.admin_approved_at else (request_obj.paid_at.strftime('%Y-%m-%d') if request_obj.paid_at else 'N/A')
        payment_date = request_obj.payment_date.strftime('%Y-%m-%d') if request_obj.payment_date else (request_obj.paid_at.strftime('%Y-%m-%d') if request_obj.paid_at else 'N/A')
        requester_name = f"{request_obj.first_name} {request_obj.last_name}".strip() or 'N/A'
        treasurer_name = request_obj.treasurer_name or 'N/A'
        treasurer_phone = request_obj.treasurer_phone or 'N/A'
        department = str(request_obj.department) if request_obj.department else 'N/A'
        payment_form_number = request_obj.form_number.replace('EXP-', 'PAY-') if request_obj.form_number.startswith('EXP-') else f'PAY-{request_obj.form_number}'
        amount_paid = f"TZS {request_obj.total_amount:,.2f}"
        items = [[str(i+1), item.description, f"{item.amount:,.2f}"] for i, item in enumerate(request_obj.items.all())]
        phone_number = getattr(request_obj, 'phone_number', 'N/A') or 'N/A'
    else:  # RetirementForm
        request_date = request_obj.date_of_request.strftime('%Y-%m-%d') if request_obj.date_of_request else 'N/A'
        final_approval_date = request_obj.admin_approved_at.strftime('%Y-%m-%d') if request_obj.admin_approved_at else (request_obj.paid_at.strftime('%Y-%m-%d') if request_obj.paid_at else 'N/A')
        payment_date = request_obj.payment_date.strftime('%Y-%m-%d') if request_obj.payment_date else (request_obj.paid_at.strftime('%Y-%m-%d') if request_obj.paid_at else 'N/A')
        requester_name = f"{request_obj.first_name} {request_obj.last_name}".strip() or 'N/A'
        treasurer_name = request_obj.treasurer_name or 'N/A'
        treasurer_phone = request_obj.treasurer_phone or 'N/A'
        department = str(request_obj.department) if request_obj.department else 'N/A'
        payment_form_number = request_obj.form_number.replace('RET-', 'PAY-') if request_obj.form_number.startswith('RET-') else f'PAY-{request_obj.form_number}'
        amount_paid = f"TZS {request_obj.total_amount:,.2f}"
        items = [[str(i+1), item.description, f"{item.amount:,.2f}"] for i, item in enumerate(request_obj.items.all())]
        phone_number = getattr(request_obj, 'phone_number', 'N/A') or 'N/A'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=20, bottomMargin=20, leftMargin=20, rightMargin=20)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'title', parent=styles['Heading1'], fontSize=18, leading=22,
        alignment=TA_CENTER, textColor=colors.HexColor('#003366'), fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'subtitle', parent=styles['Normal'], fontSize=10, leading=14,
        alignment=TA_CENTER, textColor=colors.HexColor('#003366'), fontName='Helvetica-Bold'
    )
    normal_center = ParagraphStyle('normal_center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10)
    label_style = ParagraphStyle('label', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold')
    value_style = ParagraphStyle('value', parent=styles['Normal'], fontSize=10, leading=12)
    note_style = ParagraphStyle('note', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.grey)

    if logo_path and os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=70, height=70)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 6))
        except:
            pass

    story.append(Paragraph('SEVENTH-DAY ADVENTIST CHURCH', title_style))
    story.append(Paragraph('EAST-CENTRAL TANZANIA CONFERENCE', subtitle_style))
    story.append(Paragraph('PO BOX 105, Bagamoyo', normal_center))
    story.append(Spacer(1, 10))
    story.append(Paragraph('PAYMENT FORM', ParagraphStyle('heading', parent=styles['Heading2'], fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=colors.HexColor('#003366'))))
    story.append(Spacer(1, 12))

    header_data = [
        ['Payment Form No:', payment_form_number],
        ['Date of Request:', request_date],
        ['Date of Final Approval:', final_approval_date],
        ['Date of Payment:', payment_date],
        ['Requester:', requester_name],
        ['Department:', department],
        ['Mtaa:', location_mtaa],
        ['PO Box:', location_pobox],
        ['Kanisa:', kanisa],
        ['Phone:', phone_number],
        ['Treasurer:', treasurer_name],
        ['Amount Paid (TZS):', amount_paid],
    ]

    header_table = Table(header_data, colWidths=[130, 340])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f0fe')),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f2f6fb')),
        ('LINEABOVE', (0, 0), (-1, -1), 0.25, colors.HexColor('#d9e4f5')),
        ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#d9e4f5')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 14))

    if is_expense and getattr(request_obj, 'reason', None):
        reason_table = Table([
            ['Reason for Payment:', request_obj.reason]
        ], colWidths=[130, 340])
        reason_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f2f6fb')),
            ('BACKGROUND', (1, 0), (1, 0), colors.white),
            ('LINEABOVE', (0, 0), (-1, -1), 0.25, colors.HexColor('#d9e4f5')),
            ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#d9e4f5')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(reason_table)
        story.append(Spacer(1, 12))

    details_data = [['#', 'Description', 'Amount (TZS)']]
    for item in items:
        details_data.append([item[0], item[1], item[2]])
    if len(details_data) == 1:
        details_data.append(['', 'No items listed', ''])
    details_data.append(['', 'TOTAL', amount_paid])

    details_table = Table(details_data, colWidths=[30, 330, 110])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d3d9e6')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#003366')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 20))

    sig_data = [
        [Paragraph('REQUESTER', label_style), Paragraph('TREASURER', label_style)],
        [Paragraph(f'Name: {requester_name}', value_style), Paragraph(f'Name: {treasurer_name}', value_style)],
        [Paragraph('Signature: ___________________________', value_style), Paragraph('Signature: ___________________________', value_style)],
        [Paragraph('Date: ________________________________', value_style), Paragraph('Date: ________________________________', value_style)],
    ]
    sig_table = Table(sig_data, colWidths=[235, 235], hAlign='CENTER')
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 18))
    story.append(Paragraph('This payment form is valid only when signed and dated by the treasurer.', note_style))
    story.append(Paragraph('Thank you for your cooperation and faithful stewardship.', note_style))

    doc.build(story)
    buffer.seek(0)
    return buffer