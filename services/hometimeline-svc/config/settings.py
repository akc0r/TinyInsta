import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "hometimeline-svc"
INSTALLED_APPS += ["timeline"]  # noqa: F405

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/2")

USERTIMELINE_URL = os.environ.get("USERTIMELINE_URL", "http://usertimeline-svc:8000")
CELEBRITY_FOLLOWER_THRESHOLD = int(os.environ.get("CELEBRITY_FOLLOWER_THRESHOLD", "5000"))

# Algorithmic re-rank of the home feed via ranking-svc. Off → pure chronological.
RANKING_ENABLED = os.environ.get("RANKING_ENABLED", "false").lower() == "true"
RANKING_URL = os.environ.get("RANKING_URL", "http://ranking-svc:8000")
