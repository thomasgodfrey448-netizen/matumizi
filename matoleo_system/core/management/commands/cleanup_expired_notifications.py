from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Notification


class Command(BaseCommand):
    help = 'Delete read notifications that are older than 24 hours'

    def handle(self, *args, **options):
        # Calculate cutoff time (24 hours ago)
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # Find and delete expired read notifications
        expired_notifs = Notification.objects.filter(
            is_read=True,
            read_at__lt=cutoff_time
        )
        
        count = expired_notifs.count()
        expired_notifs.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {count} expired notification(s)'
            )
        )
