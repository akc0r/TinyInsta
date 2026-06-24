import uuid

from django.db import models


class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author_id = models.UUIDField()
    media_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "stories"
        indexes = [models.Index(fields=["author_id", "expires_at"])]


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views")
    viewer_id = models.UUIDField()
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_views"
        constraints = [
            models.UniqueConstraint(fields=["story", "viewer_id"], name="uniq_story_view"),
        ]
