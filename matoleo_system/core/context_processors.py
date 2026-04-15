import logging
from .models import Notification

logger = logging.getLogger(__name__)


def notifications_processor(request):
    try:
        if request.user.is_authenticated:
            try:
                # Single query: fetch the 5 most recent notifications for the user
                recent_notifications = list(
                    Notification.objects.filter(recipient=request.user)
                    .order_by('-created_at')[:5]
                )
                unread_count = sum(1 for n in recent_notifications if not n.is_read)
                # If unread notifications extend beyond the 5 fetched, do a count query
                if unread_count == 5:
                    unread_count = Notification.objects.filter(
                        recipient=request.user, is_read=False
                    ).count()
                return {
                    'unread_notifications_count': unread_count,
                    'recent_notifications': recent_notifications,
                }
            except Exception as e:
                logger.exception(f"Error fetching notifications for user {request.user.id}: {e}")
                return {
                    'unread_notifications_count': 0,
                    'recent_notifications': [],
                }
    except Exception as e:
        logger.exception(f"Error in notifications_processor: {e}")
    return {
        'unread_notifications_count': 0,
        'recent_notifications': [],
    }


def user_role_processor(request):
    try:
        if request.user.is_authenticated:
            try:
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
            except Exception as e:
                logger.exception(f"Error getting user role for {request.user.id}: {e}")
                return {'user_role': 'User'}
    except Exception as e:
        logger.exception(f"Error in user_role_processor: {e}")
    return {'user_role': 'Guest'}
