import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "ranking-svc"
INSTALLED_APPS += ["ranking"]  # noqa: F405

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

# Redis holds the per-post engagement signal and per-(viewer, author) affinity,
# both rebuildable by replaying the post.* topics.
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/4")

# Scoring weights (env-tunable so the ranking can be tuned without a redeploy).
RANK_W_RECENCY = float(os.environ.get("RANK_W_RECENCY", "1.0"))
RANK_W_ENGAGEMENT = float(os.environ.get("RANK_W_ENGAGEMENT", "0.6"))
RANK_W_AFFINITY = float(os.environ.get("RANK_W_AFFINITY", "0.8"))
RANK_W_REEL = float(os.environ.get("RANK_W_REEL", "0.2"))  # small boost for reels
# Recency half-life in hours: a post's recency score halves every HALF_LIFE hours.
RANK_RECENCY_HALF_LIFE_H = float(os.environ.get("RANK_RECENCY_HALF_LIFE_H", "6"))
