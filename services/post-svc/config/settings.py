import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "post-svc"
INSTALLED_APPS += ["posts"]  # noqa: F405

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017/?replicaSet=rs0")
MONGO_DB = os.environ.get("MONGO_DB", "post_svc")
