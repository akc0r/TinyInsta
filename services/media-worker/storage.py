"""MinIO/S3 access for the worker (no Django — plain env config).

Mirrors media-svc/media/storage.py: object operations go through the internal
endpoint (minio:9000), while the URLs we hand out point at the public one
(localhost:9000) so the browser can fetch the variants directly.
"""

from __future__ import annotations

import os
from functools import lru_cache

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.environ.get("S3_BUCKET", "media")
S3_PUBLIC_URL = os.environ.get("S3_PUBLIC_URL", "http://localhost:9000")
# Variants are served through the CDN cache when configured (defaults to the
# public endpoint).
S3_CDN_URL = os.environ.get("S3_CDN_URL", S3_PUBLIC_URL)


@lru_cache(maxsize=1)
def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


def key_from_url(url: str) -> str:
    """Recover the object key from an object URL (`.../<bucket>/<key>`)."""
    marker = f"/{S3_BUCKET}/"
    idx = url.find(marker)
    if idx == -1:
        raise ValueError(f"cannot extract object key from url: {url}")
    return url[idx + len(marker):]


def public_url(object_key: str) -> str:
    return f"{S3_CDN_URL}/{S3_BUCKET}/{object_key}"


def download(object_key: str) -> bytes:
    return _client().get_object(Bucket=S3_BUCKET, Key=object_key)["Body"].read()


def upload(object_key: str, data: bytes, content_type: str) -> str:
    _client().put_object(
        Bucket=S3_BUCKET, Key=object_key, Body=data, ContentType=content_type
    )
    return public_url(object_key)
