from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def get_client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def presigned_put_url(object_key: str, expires: int = 3600) -> str:
    raise NotImplementedError
