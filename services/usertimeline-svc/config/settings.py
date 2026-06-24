import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "usertimeline-svc"
INSTALLED_APPS += ["timeline"]  # noqa: F405

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/1")
