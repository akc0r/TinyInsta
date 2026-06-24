import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "user-svc"
INSTALLED_APPS += ["users"]  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "user_svc"),
        "USER": os.environ.get("POSTGRES_USER", "tinyinsta"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "tinyinsta"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "tinyinsta")
