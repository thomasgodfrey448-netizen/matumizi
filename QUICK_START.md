# Quick Start Guide - Testing the Approval Workflow

## Current Credentials
- **Username**: admin
- **Password**: admin123
- **Access**: http://127.0.0.1:8000

---

## Step 1: Set Up Approvers

1. Go to Admin Dashboard: http://127.0.0.1:8000/admin_dashboard/
2. Scroll to **Departments** section - create or note existing departments
3. In **First Approvers** section:
   - Click "+ Add"
   - Select a non-admin user
   - Set Level: "First Approver"
   - Select one or more departments
   - Add phone number
   - Click "Add Approver"
4. In **Second Approvers** section:
   - Click "+ Add"
   - Select a different non-admin user
   - Set Level: "Second Approver"
   - Don't select departments (not needed for 2nd approvers)
   - Add phone number
   - Click "Add Approver"

---

## Step 2: Create Test Request

1. **Logout** from admin account
2. **Login** with a regular user account
3. Go to: http://127.0.0.1:8000/expenses/ (or retirement)
4. Click "New Expense Request"
5. Fill in the form:
   - First Name, Last Name
   - Phone Number
   - Department (same as first approver's assigned department)
   - Date
   - Reason
   - Add at least one item with amount
6. Click "Create" (saves as draft)
7. Click "Submit for Approval"

---

## Step 3: First Approver Reviews

1. **Logout** and **login** as the first approver
2. Go to Expenses Dashboard: http://127.0.0.1:8000/expenses/
3. Click on the submitted request
4. Review the details
5. Click "Approve" button (or "Reject" to test rejection)
6. If approved, status changes to "First Approved"

---

## Step 4: Second Approver Reviews

1. **Logout** and **login** as the second approver
2. Go to Expenses Dashboard
3. You should see ALL departments' requests
4. Click on the "First Approved" request
5. Click "Approve" button
6. Status changes to "Second Approved"

---

## Step 5: Admin Final Approval

1. **Logout** and **login** as admin
2. Go to Expenses Dashboard
3. Click on "Second Approved" request
4. Click "Final Approval" button
5. Status changes to "Approved"
6. **Download PDF** to see the complete form with approver signatures

---

## Step 6: Test PDF Download

1. On any request detail page, click **"Download PDF"** button
2. PDF should include:
   - Church name and department
   - Form details and items
   - Approver names (auto-filled after approval)
   - Phone numbers
   - Signature lines for all three approvers
   - Church logo at top (if added)

---

## Adding Church Logo

1. Find or create a PNG/JPG image of your church logo (200×200px recommended)
2. Save it to: `matoleo_system/static/images/church_logo.png`
3. Future PDFs will automatically include the logo

---

## Key Features to Test

✅ **Permission Checks**
- Regular user can only see their own requests
- First approver sees only their department's requests
- Second approver sees ALL requests
- Admin sees all requests and can do final approval

✅ **Notifications**
- Check "Notifications" bell icon for updates at each stage
- Should see notifications for new submissions and approval requests

✅ **Status Tracking**
- Watch status change through: Draft → Submitted → First Approved → Second Approved → Approved
- Color badges change at each stage

✅ **Approval Details**
- Approver names auto-populate on approval
- Phone numbers pulled from approver profiles
- Timestamps recorded for each approval

✅ **Rejection Workflow**
- Reject at any stage with reason
- Request goes back to "Rejected" status
- User receives notification with rejection reason
- User can edit and resubmit

✅ **PDF Generation**
- Download works from detail page
- Signature section visible
- All approver details populated
- Church logo displays if added

---

## Troubleshooting

**Q: First approver sees all requests instead of just their department?**
- A: Check they're assigned to the department in approver modal
- A: Verify department matches the request's department

**Q: PDF not showing approver names?**
- A: Request must be approved first for names to populate
- A: Check approver profile is complete

**Q: Logo not showing in PDF?**
- A: Add church logo to: `static/images/church_logo.png`
- A: Ensure image is readable and not corrupted

**Q: Notifications not appearing?**
- A: Check user's notification page: /notifications/
- A: Ensure correct user is logged in for role testing

---

## Admin Dashboard Features

Once an approver is created, go back to admin dashboard to see:
- First Approvers list with assigned departments
- Second Approvers list
- Treasurers list
- Separate Regular Users and Admin Users sections
- Pending Approvals counter
- Create/manage all user types from dashboard

---

**Status**: System ready for comprehensive testing!
**Support Files**: Check `IMPLEMENTATION_GUIDE.md` for detailed technical information.
