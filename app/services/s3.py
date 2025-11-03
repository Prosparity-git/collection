import uuid
import boto3
from botocore.config import Config as BotoConfig
from app.core.config import settings

# Hardcoded AWS S3 configuration (requested to avoid env usage)

_session = boto3.session.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
_s3 = _session.client("s3", config=BotoConfig(signature_version="s3v4"))


def make_key_for_document(loan_application_id: int, agent_id: int, filename: str) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    return f"{settings.S3_PREFIX}loan/{loan_application_id}/{agent_id}/{uuid.uuid4()}.{ext}"


def presign_put(key: str, content_type: str) -> str:
    return _s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.PRESIGNED_TTL_SECONDS,
    )


def public_url(key: str) -> str:
    if settings.CLOUDFRONT_URL:
        return f"{settings.CLOUDFRONT_URL}/{key}"
    return f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{key}"


def presign_post(key: str, content_type: str) -> dict:
    """Generate a presigned POST so clients can upload with HTTP POST multipart/form-data.

    Returns a dict with 'url' and 'fields' suitable to send as form-data along with the file.
    """
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    return _s3.generate_presigned_post(
        Bucket=S3_BUCKET,
        Key=key,
        Fields={
            "Content-Type": content_type,
        },
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, max_bytes],
        ],
        ExpiresIn=settings.PRESIGNED_TTL_SECONDS,
    )


# Generate a time-limited signed GET URL for private objects
def presign_get(key: str, expires_in_seconds: int | None = None) -> str:
    ttl = expires_in_seconds or settings.PRESIGNED_TTL_SECONDS
    return _s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": S3_BUCKET,
            "Key": key,
        },
        ExpiresIn=ttl,
    )