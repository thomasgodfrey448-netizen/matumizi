# Matoleo System — Makong Juu SDA Church Finance Department

A full-featured Django web application for managing expense requests and retirement forms with a multi-level approval workflow.

---

## Features

- **Expense Request Module** — Create, edit, submit, and track expense requests with itemized line items
- **Retirement Form Module** — Submit and track retirement/accountability forms
- **3-Level Approval Workflow** — First Approver → Second Approver → Admin final approval
- **Notification System** — Real-time in-app notifications at each approval stage
- **Reports Dashboard** — Filter, search, and download PDF reports for expenses and retirements
- **Admin Panel** — Manage departments, approvers, registration codes, announcements, and users
- **PDF Download** — Professional SDA Church-branded PDF forms for each request
- **Role-Based Access** — Users, First Approvers, Second Approvers, and Admins

---

## Quick Start

### Requirements
- Python 3.10+
- pip

### Installation

```bash
# 1. Clone or extract the project
cd matoleo_system

# 2. Install dependencies
pip install django pillow django-crispy-forms crispy-bootstrap5 django-widget-tweaks reportlab

# 3. Run migrations
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Seed initial data (departments, registration code, sample approver)
python manage.py shell -c "
from django.contrib.auth.models import User
from core.models import Department, RegistrationCode

depts = ['Youth Department','Sabbath School','Community Services','Health Ministry',
         'Education','Music Ministry','Women Ministry','Men Ministry',
         'Finance Committee','Building Committee','Evangelism','Children Ministry']
for d in depts:
    Department.objects.get_or_create(name=d)

admin = User.objects.get(username='admin')  # replace with your superuser username
RegistrationCode.objects.get_or_create(
    code='MATOLEO2024',
    defaults={'created_by': admin, 'max_uses': 100}
)
print('Seeded!')
"

# 6. Run the server
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

---

## Default Credentials (Demo)

| Role | Username | Password |
|------|----------|----------|
| Super Admin | `admin` | `admin123` |
| 2nd Approver | `yohana.sefue` | `yohana123` |

> **Change these passwords immediately in production!**

---

## Registration Code

The default registration code for new users is: **`MATOLEO2024`**

Admins can generate new codes from the Admin Panel.

---

## User Roles

| Role | Capabilities |
|------|-------------|
| **User** | Create/edit/submit expense & retirement forms, view own forms |
| **First Approver** | View and approve submitted forms for their department |
| **Second Approver** | View and approve first-approved forms |
| **Admin (Staff)** | Final approval, manage all users/departments/approvers, view all reports |

---

## Approval Workflow

```
User submits form
      ↓
First Approver (department-specific) approves
      ↓
Second Approver approves
      ↓
Admin gives final approval
      ↓
Form marked as APPROVED ✓
```

At each step, the next approver receives an in-app notification.

---

## Project Structure

```
matoleo_system/
├── accounts/          # User authentication (login, register, profile)
├── core/              # Home, notifications, admin panel, models (UserProfile, Department, Approver)
├── expenses/          # Expense request CRUD, approval workflow, PDF download
├── retirement/        # Retirement form CRUD, approval workflow, PDF download
├── reports/           # Reports dashboard, PDF bulk reports
├── static/
│   ├── css/main.css   # Dark blue gradient design system
│   └── js/main.js     # Dynamic form rows, sidebar toggle, auto-dismiss alerts
├── templates/         # All HTML templates
│   ├── base.html      # Sidebar layout
│   ├── accounts/      # Login, register, profile
│   ├── core/          # Home, notifications, admin dashboard
│   ├── expenses/      # Expense form, dashboard, detail
│   ├── retirement/    # Retirement form, dashboard, detail
│   └── reports/       # Reports dashboard
└── manage.py
```

---

## Technology Stack

- **Backend**: Django 4.x, SQLite (easily switchable to PostgreSQL/MySQL)
- **Frontend**: Custom CSS (dark blue gradient), Bootstrap 5 grid, Font Awesome 6
- **PDF Generation**: ReportLab
- **Forms**: django-widget-tweaks, crispy-bootstrap5

---

## Production Deployment Notes

1. Set `DEBUG = False` in `settings.py`
2. Set a strong `SECRET_KEY`
3. Configure `ALLOWED_HOSTS` with your domain
4. Use PostgreSQL or MySQL instead of SQLite
5. Set up a proper email backend for notifications
6. Use Gunicorn + Nginx for serving

---

*Developed for Makong Juu SDA Church Finance Department — Matoleo System*
