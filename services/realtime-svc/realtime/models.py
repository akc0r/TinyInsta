import uuid

from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        LIKE = "like"
        COMMENT = "comment"
        FOLLOW = "follow"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField()
    type = models.CharField(max_length=16, choices=Type.choices)
    payload = models.JSONField(default=dict)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        indexes = [models.Index(fields=["user_id", "read"])]
        ordering = ["-created_at"]
