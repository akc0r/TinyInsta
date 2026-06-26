from functools import lru_cache

from django.conf import settings


def _build_client(endpoint_url: str):
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )


@lru_cache(maxsize=1)
def get_client():
    """Client for server-side object operations (internal endpoint)."""
    return _build_client(settings.S3_ENDPOINT)


@lru_cache(maxsize=1)
def get_public_client():
    """Client used to presign URLs the browser calls directly.

    A presigned signature is bound to the host in the URL, so it must be
    computed against the public endpoint (localhost:9000), not minio:9000.
    """
    return _build_client(settings.S3_PUBLIC_URL)


def presigned_put_url(object_key: str, expires: int = 3600) -> str:
    return get_public_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": object_key},
        ExpiresIn=expires,
    )


def object_url(object_key: str) -> str:
    # Reads go through the CDN cache (S3_CDN_URL); uploads keep using S3_PUBLIC_URL.
    return f"{settings.S3_CDN_URL}/{settings.S3_BUCKET}/{object_key}"
