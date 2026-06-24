from django.db import models


class Like(models.Model):
    post_id = models.UUIDField()
    user_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "likes"
        constraints = [
            models.UniqueConstraint(fields=["post_id", "user_id"], name="uniq_like"),
        ]
        indexes = [models.Index(fields=["post_id"])]
