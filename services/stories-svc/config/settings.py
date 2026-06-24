import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "stories-svc"
INSTALLED_APPS += ["stories"]  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "stories_svc"),
        "USER": os.environ.get("POSTGRES_USER", "tinyinsta"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "tinyinsta"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/4")
STORY_TTL_SECONDS = int(os.environ.get("STORY_TTL_SECONDS", str(24 * 3600)))
