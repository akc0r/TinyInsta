from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from stories.models import Story


class Command(BaseCommand):
    help = "Purge expired stories from Postgres (the read path already filters "
    "on expires_at; this just reclaims storage). Run periodically, e.g. via cron."

    def handle(self, *args, **options):
        deleted, _ = Story.objects.filter(
            expires_at__lte=datetime.now(timezone.utc)
        ).delete()
        # story_views rows cascade with their parent story.
        self.stdout.write(f"Swept {deleted} expired story rows")
