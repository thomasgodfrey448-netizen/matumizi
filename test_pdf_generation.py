#!/usr/bin/env python
"""
Test script to verify PDF generation with WeasyPrint
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'matoleo_system'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matoleo_system.settings')
django.setup()

from django.template.loader import render_to_string
from weasyprint import HTML
from retirement.models import RetirementForm
from expenses.models import ExpenseRequest

def test_retirement_pdf():
    """Test retirement PDF generation"""
    try:
        # Get a sample retirement form
        form = RetirementForm.objects.first()
        if not form:
            print("No retirement forms found in database")
            return False

        print(f"Testing PDF generation for retirement form: {form.form_number}")

        # Generate HTML
        html_string = render_to_string('pdf/retirement_form.html', {
            'form': form,
        })

        # Create PDF
        html_doc = HTML(string=html_string)
        pdf_bytes = html_doc.write_pdf()

        # Save to file for testing
        with open('test_retirement.pdf', 'wb') as f:
            f.write(pdf_bytes)

        print("✓ Retirement PDF generated successfully")
        return True

    except Exception as e:
        print(f"✗ Error generating retirement PDF: {e}")
        return False

def test_expense_pdf():
    """Test expense PDF generation"""
    try:
        # Get a sample expense form
        form = ExpenseRequest.objects.first()
        if not form:
            print("No expense forms found in database")
            return False

        print(f"Testing PDF generation for expense form: {form.form_number}")

        # Generate HTML
        html_string = render_to_string('pdf/expense_form.html', {
            'form': form,
        })

        # Create PDF
        html_doc = HTML(string=html_string)
        pdf_bytes = html_doc.write_pdf()

        # Save to file for testing
        with open('test_expense.pdf', 'wb') as f:
            f.write(pdf_bytes)

        print("✓ Expense PDF generated successfully")
        return True

    except Exception as e:
        print(f"✗ Error generating expense PDF: {e}")
        return False

if __name__ == '__main__':
    print("Testing PDF generation with WeasyPrint...")

    retirement_success = test_retirement_pdf()
    expense_success = test_expense_pdf()

    if retirement_success and expense_success:
        print("\n✓ All PDF generation tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some PDF generation tests failed!")
        sys.exit(1)