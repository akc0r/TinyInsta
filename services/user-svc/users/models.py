from django.db import models


class Profile(models.Model):
    # Primary key = the Keycloak token `sub`; always set explicitly on creation.
    user_id = models.UUIDField(primary_key=True, editable=False)
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150, blank=True, default="")
    bio = models.TextField(blank=True, default="")
    link = models.URLField(blank=True, default="")
    avatar_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "profiles"
