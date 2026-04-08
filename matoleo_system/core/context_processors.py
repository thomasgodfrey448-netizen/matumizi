from .models import Notification

def notifications_processor(request):
    try:
        if request.user.is_authenticated:
            unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
            recent_notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:5]
            return {
                'unread_notifications_count': unread_count,
                'recent_notifications': recent_notifications,
            }
    except Exception as e:
        print(f"Error in notifications_processor: {e}")
        return {
            'unread_notifications_count': 0,
            'recent_notifications': [],
        }
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }


def user_role_processor(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            role = 'Super Admin'
        elif request.user.is_staff:
            role = 'Admin'
        elif hasattr(request.user, 'treasurer_profile'):
            role = 'Treasurer'
        elif hasattr(request.user, 'approver_profile'):
            role = request.user.approver_profile.get_level_display()
        else:
            role = 'User'
        return {'user_role': role}
    return {'user_role': 'Guest'}
