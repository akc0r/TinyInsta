import os

from tinyinsta.service.settings import *  # noqa: F401,F403

SERVICE_NAME = "media-svc"
INSTALLED_APPS += ["media"]  # noqa: F405

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.environ.get("MONGO_DB", "media_svc")

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.environ.get("S3_BUCKET", "media")
S3_PUBLIC_URL = os.environ.get("S3_PUBLIC_URL", "http://localhost:9000")
# Read URLs are served through the caching CDN (nginx in front of MinIO) when
# set; falls back to the public endpoint so uploads (presigned PUT, host-bound)
# always go straight to MinIO.
S3_CDN_URL = os.environ.get("S3_CDN_URL", S3_PUBLIC_URL)
