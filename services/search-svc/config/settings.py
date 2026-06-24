import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "search-svc"
INSTALLED_APPS += ["search"]  # noqa: F405

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")
