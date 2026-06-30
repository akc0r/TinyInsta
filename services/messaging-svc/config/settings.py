import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "messaging-svc"
INSTALLED_APPS += ["messaging"]  # noqa: F405

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

# Cassandra (direct messages).
CASSANDRA_HOSTS = os.environ.get("CASSANDRA_HOSTS", "cassandra").split(",")
CASSANDRA_PORT = int(os.environ.get("CASSANDRA_PORT", "9042"))
CASSANDRA_KEYSPACE = os.environ.get("CASSANDRA_KEYSPACE", "messaging")
CASSANDRA_REPLICATION = int(os.environ.get("CASSANDRA_REPLICATION", "1"))
