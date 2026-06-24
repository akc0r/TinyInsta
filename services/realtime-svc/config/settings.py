import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "realtime-svc"
INSTALLED_APPS += ["channels", "realtime"]  # noqa: F405

ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "realtime_svc"),
        "USER": os.environ.get("POSTGRES_USER", "tinyinsta"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "tinyinsta"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/5")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}
