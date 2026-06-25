import uuid

from django.db import models


class Story(models.Model):
    class Audience(models.TextChoices):
        PUBLIC = "public", "Public"
        CLOSE_FRIENDS = "close_friends", "Close friends"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author_id = models.UUIDField()
    media_id = models.UUIDField()
    audience = models.CharField(
        max_length=16, choices=Audience.choices, default=Audience.PUBLIC
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "stories"
        indexes = [
            models.Index(
                fields=["author_id", "expires_at"], name="stories_author_expires_idx"
            )
        ]


class StoryView(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views")
    viewer_id = models.UUIDField()
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "story_views"
        constraints = [
            models.UniqueConstraint(fields=["story", "viewer_id"], name="uniq_story_view"),
        ]
