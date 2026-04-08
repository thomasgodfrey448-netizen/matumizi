from django import template
from django.utils.html import mark_safe

register = template.Library()


@register.filter
def approval_status_badge(obj):
    """
    Display approval status with visual indicators
    """
    html = '<div class="approval-status">'
    
    # First Approver Status
    if hasattr(obj, 'first_approver_approved'):
        status = obj.first_approver_approved
        icon = '✓' if status else '◯'
        color = 'success' if status else 'secondary'
        html += f'<span class="badge bg-{color}">First Approver {icon}</span> '
    
    # Second Approver Status
    if hasattr(obj, 'second_approver_approved'):
        status = obj.second_approver_approved
        icon = '✓' if status else '◯'
        color = 'success' if status else 'secondary'
        html += f'<span class="badge bg-{color}">Second Approver {icon}</span> '
    
    # Treasurer Status
    if hasattr(obj, 'treasurer_approved'):
        status = obj.treasurer_approved
        icon = '✓' if status else '◯'
        color = 'success' if status else 'secondary'
        html += f'<span class="badge bg-{color}">Treasurer {icon}</span>'
    
    html += '</div>'
    return mark_safe(html)


@register.filter
def approval_status_color(status):
    """
    Returns color for approval status
    """
    if status == 'approved':
        return 'success'
    elif status == 'rejected':
        return 'danger'
    elif status == 'pending':
        return 'warning'
    return 'secondary'
