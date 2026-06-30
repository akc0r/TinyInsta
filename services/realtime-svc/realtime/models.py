import uuid

from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        LIKE = "like"
        COMMENT = "comment"
        FOLLOW = "follow"
        MENTION = "mention"
        REPOST = "repost"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    type = models.CharField(max_length=16, choices=Type.choices)
    payload = models.JSONField(default=dict)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        indexes = [models.Index(fields=["user_id", "read"], name="notif_user_read_idx")]
        ordering = ["-created_at"]


class UserHandle(models.Model):
    """username → user_id projection, built from user.created.

    Used to resolve an @mention (a raw username) to the user to notify.
    """

    user_id = models.UUIDField(primary_key=True)
    username = models.CharField(max_length=150, unique=True, db_index=True)

    class Meta:
        db_table = "user_handles"
