# Matoleo System - Approval Workflow Implementation Guide

## Overview
This document summarizes all the changes implemented to support a comprehensive approval workflow with multiple approver roles, notifications, and PDF generation with digital signature tracking.

---

## ✅ Implemented Features

### 1. **Approver Roles & Permissions**

#### First Approver
- Login access enabled
- Restricted view: Only sees requests from their assigned departments
- Permissions:
  - Approve/Reject expense requests (first level)
  - Approve/Reject retirement forms (first level)
- Department Assignment: Can be assigned to multiple departments
- Phone Number: Configurable per approver

#### Second Approver
- Login access enabled
- Unrestricted view: Can see all departments' requests (like admin)
- Permissions:
  - Approve requests already approved by first approver
  - Approve/Reject requests
- Department Assignment: Not applicable (empty)

#### Notification System
- Both approver levels receive notifications for new submissions
- First approvers notified of new requests in their departments
- Second approvers notified when first approval is complete
- Admins notified when second approval is complete

### 2. **Approval Status Indicators**

Visual indicators added throughout the application:

#### Dashboard Display
- Progress bars showing approval stages:
  - Submitted → First Approval → Second Approval → Final Approval
  - Color-coded badges: Draft (gray), Submitted (blue), First Approved (green), Second Approved (purple), Approved (teal), Rejected (red)

#### Detail Pages
- Approval cards showing:
  - Approver name and phone number
  - Date of approval
  - Status with checkmark vs pending indicator

#### Admin Dashboard
- Separate sections for:
  - First Approvers (with assigned departments)
  - Second Approvers
  - Treasurers
  - Regular Users
  - Admin Users
- Statistics showing pending approvals count

### 3. **Form Structure with Approver Fields**

All forms (Expenses & Retirements) include sections for:

```
├─ Employee Information
│  ├─ Name
│  ├─ Phone
│  ├─ Department
│  └─ Date
│
├─ Request Details
│  ├─ Reason/Purpose
│  ├─ Items/Description
│  └─ Amount
│
├─ Approvals Section
│  ├─ First Approver
│  │  ├─ Name (auto-filled on approval)
│  │  ├─ Phone (from approver profile)
│  │  └─ Signature (PDF only)
│  ├─ Second Approver
│  │  ├─ Name (auto-filled on approval)
│  │  ├─ Phone (from approver profile)
│  │  └─ Signature (PDF only)
│  └─ Treasurer
│     ├─ Name
│     ├─ Phone
│     └─ Signature (PDF only)
│
└─ Status & Timestamps
   ├─ Created date
   ├─ Submitted date
   ├─ First approval date
   ├─ Second approval date
   └─ Final approval date
```

### 4. **First Approver Admin Management**

In Django Admin or Admin Dashboard:

```
Create/Edit First Approver:
├─ Select User Account
├─ Set Approver Level: "First Approver"
├─ Assign Departments (Multi-select)
│  └─ Can assign to multiple departments
├─ Set Phone Number
└─ Toggle Active Status
```

**Key Feature**: First approvers can be assigned to multiple departments from which they will see requests.

### 5. **Approver Profiles**

#### Changes Made
- ✅ "My Activities" section removed from user profile
- Profile now shows:
  - User basic information
  - Role badge (User, Admin, First Approver, Second Approver)
  - Edit personal information form
  - Change password form
  - (Activity section removed as requested)

### 6. **Admin Dashboard Enhancements**

The admin dashboard now features:

#### Statistics Cards
- Regular Users count
- Admin Users count
- First Approvers count
- Second Approvers count
- Treasurers count
- Pending Approvals count (all), requests awaiting action)

#### Separate Management Sections
- **Departments**: Full CRUD operations
- **First Approvers**: List with assigned departments, phone, active status
- **Second Approvers**: List with phone and active status
- **Treasurers**: List with phone and active status
- **Regular Users**: List with delete functionality
- **Admin Users**: List with delete functionality
- **Registration Codes**: Generate and manage
- **Announcements**: Create and manage

#### Action Modals
- Add Department Modal
- Add Approver Modal (with department multi-select for first approvers)
- Add Treasurer Modal
- Add Announcement Modal

### 7. **PDF Generation with Church Logo**

#### PDF Features
- **Logo Support**: Church logo displayed at top of PDF
  - Path: `static/images/church_logo.png`
  - Size: 25mm × 25mm
  - Gracefully skips if not found

#### PDF Content Sections
1. **Header**
   - Church name and department
   - Form title (Expense Request / Retirement Form)

2. **Form Information**
   - Form number
   - Employee name and phone
   - Department
   - Date
   - Submission status

3. **Request Details**
   - Items/Description with amounts
   - Total amount (highlighted)

4. **Approvals Section**
   - Three-column signature area:
     - First Approver (name, signature line, phone)
     - Second Approver (name, signature line, phone)
     - Treasurer (name, signature line, phone)
   - Auto-filled from form data on approval

5. **Styling**
   - Professional color scheme (dark blue headers)
   - Readable table formatting
   - Currency formatting (TZS)

#### PDF Download Locations
- **Expenses**: `/expenses/{id}/download/`
- **Retirements**: `/retirement/{id}/download/`

### 8. **System Logo Handling**

To add the church logo:
1. Place your church logo image at: `matoleo_system/static/images/church_logo.png`
2. Supported formats: PNG, JPG, JPEG, GIF, WebP
3. Recommended size: 200×200px (will be resized to 25×25mm in PDF)
4. The system will gracefully display without logo if file doesn't exist

---

## 📁 File Changes Summary

### Models Updated
- `core/models.py`: 
  - Approver model - supports multiple departments
  - UserProfile model - shows role methods
  - Treasurer model - for treasurers

- `expenses/models.py`:
  - Added approver tracking fields
  - Added signature-related fields

- `retirement/models.py`:
  - Added approver tracking fields
  - Added signature-related fields

### Views Created/Updated
- `core/views.py`:
  - admin_dashboard: Enhanced with separate user lists
  - add_approver: Updated to handle multiple departments
  - add_treasurer: New treasurer management
  - remove_approver, remove_treasurer: Cleanup functions

- `expenses/views.py`:
  - Added PDF generation support (reportlab)
  - download_expense_pdf: Complete PDF export with approvals

- `retirement/views.py`:
  - PDF support ready (similar to expenses)

### Templates Updated
- `accounts/profile.html`:
  - Removed "My Activities" section

- `core/admin_dashboard.html`:
  - Expanded stats showing all approver types
  - Separated user management sections
  - Multi-select for departments in approver modal
  - JavaScript for dynamic form field visibility

- `expenses/detail.html`:
  - PDF download button present
  - Approval status indicators
  - Signature section visible

- `retirement/detail.html`:
  - PDF download button
  - Approval status indicators

### New Files Created
- `core/pdf_utils.py`: 
  - `generate_pdf_with_logo()`: Generic PDF generator
  - `expense_to_pdf()`: Expense-specific PDF conversion
  - `retirement_to_pdf()`: Retirement-specific PDF conversion

- `core/templatetags/approval_status.py`:
  - `approval_status_badge`: Template filter for status display
  - `approval_status_color`: Template filter for color styling

### URLs
- All routes already configured in:
  - `expenses/urls.py`
  - `retirement/urls.py`
  - `core/urls.py`

---

## 🔄 Approval Workflow Sequence

### Expense Request Lifecycle

```
1. User Creates Draft
   └─ Status: "draft"
   └─ Can edit/delete

2. User Submits Request
   └─ Status: "submitted"
   └─ Notification → First Approvers (in department)
   └─ Can no longer edit

3. First Approver Reviews & Approves
   └─ Status: "first_approved"
   └─ Name/Phone auto-filled from approver profile
   └─ Notification → Second Approvers
   └─ Can reject with reason

4. Second Approver Reviews & Approves
   └─ Status: "second_approved"
   └─ Name/Phone auto-filled from approver profile
   └─ Notification → Admins
   └─ Can reject with reason

5. Admin Final Approval
   └─ Status: "approved"
   └─ Form complete
   └─ PDF can be downloaded

6. Any Point: Rejection
   └─ Status: "rejected"
   └─ Rejection reason displayed
   └─ User can re-edit and resubmit (draft mode)
```

---

## 🔐 Permission Matrix

| Action | User | 1st Approver | 2nd Approver | Admin |
|--------|------|--------------|--------------|-------|
| Create Request | ✅ | ❌ | ❌ | ❌ |
| View Own | ✅ | ❌ | ❌ | ❌ |
| View Dept. | ❌ | ✅* | ❌ | ❌ |
| View All | ❌ | ❌ | ✅ | ✅ |
| 1st Approve | ❌ | ✅* | ❌ | ❌ |
| 2nd Approve | ❌ | ❌ | ✅ | ❌ |
| Final Approve | ❌ | ❌ | ❌ | ✅ |
| Manage Users | ❌ | ❌ | ❌ | ✅ |
| Download PDF | ✅ | ✅ | ✅ | ✅ |

*First Approvers: Only for assigned departments

---

## 📊 Database Fields Added

### ExpenseRequest Model
- `first_approver_name`: CharField (auto-filled on approval)
- `first_approver_phone`: CharField (auto-filled from profile)
- `first_approved_at`: DateTimeField (timestamp)
- `second_approver_name`: CharField (auto-filled on approval)
- `second_approver_phone`: CharField (auto-filled from profile)
- `second_approved_at`: DateTimeField (timestamp)
- `treasurer_name`: CharField (for PDF)
- `treasurer_phone`: CharField (for PDF)

### RetirementForm Model
- Same as ExpenseRequest

---

## 🧪 Testing Checklist

- [ ] Create first approver and assign to department
- [ ] Create second approver (no department needed)
- [ ] Create regular user and submit expense request
- [ ] Verify first approver sees only their department's requests
- [ ] Verify second approver sees all requests
- [ ] Test approval workflow (first → second → admin)
- [ ] Test rejection at each stage
- [ ] Download PDF and verify:
  - [ ] Church logo appears
  - [ ] Approver names populated
  - [ ] Phone numbers correct
  - [ ] Signature sections present
- [ ] Test notifications sent at each stage
- [ ] Verify "My Activities" removed from profile
- [ ] Check admin dashboard shows all sections

---

## 🚀 Deployment Notes

### Dependencies Added
```
pip install reportlab
```

### Environment Setup
- No additional environment variables required
- Ensure `static/images/` directory exists (for logo)

### Database
- All migrations applied
- No new migrations required

### Static Files
```bash
python manage.py collectstatic --noinput
```

---

## 📝 Future Enhancement suggestions

1. **Email Notifications**: Enhance system notifications with email
2. **Audit Trail**: Log all approval actions
3. **Bulk Operations**: Approve multiple requests at once
4. **Digital Signatures**: Integration with digital signature services
5. **Workflow Templates**: Customize approval workflows per expense type
6. **Budget Tracking**: Track spending against department budgets
7. **Analytics Dashboard**: Generate spending reports

---

## 🆘 Troubleshooting

### Church Logo Not Showing in PDF
- Check file exists at: `static/images/church_logo.png`
- Verify file is readable and proper image format
- Truncate to 25×25mm in PDF (configurable in pdf_utils.py)

### Approver Permissions Issues
- Ensure approver has assigned departments (first level)
- Check `is_active` flag is True
- Verify user has approver profile created

### PDF Generation Errors
- Ensure reportlab is installed: `pip install reportlab`
- Check form has submitted_by user set
- Verify database migrations completed

---

## 📞 Support

For issues or questions about the approval workflow system, refer to the implementation code:
- Model definitions: `core/models.py`, `expenses/models.py`, `retirement/models.py`
- View logic: `core/views.py`, `expenses/views.py`, `retirement/views.py`
- PDF generation: `core/pdf_utils.py`
- Templates: `templates/core/`, `templates/expenses/`, `templates/retirement/`

---

**Implementation Completed**: March 31, 2026
**System Status**: ✅ Ready for Testing
