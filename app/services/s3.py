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

def _sanitize_prefix(raw_prefix: str | None) -> str:
    """Create a safe S3 prefix from a human label.

    Only keep lowercase letters, numbers and dashes, collapse spaces to dashes,
    and always add a trailing slash. Falls back to settings.S3_PREFIX when empty.
    """
    if not raw_prefix:
        return settings.S3_PREFIX
    label = raw_prefix.strip().lower().replace(" ", "-")
    safe = "".join(ch for ch in label if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == "-")
    if not safe:
        return settings.S3_PREFIX
    if not safe.endswith("/"):
        safe = f"{safe}/"
    return safe


def make_key_for_document(
    loan_application_id: int,
    agent_id: int,
    filename: str,
    visit_type_label: str | None = None,
) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    prefix = _sanitize_prefix(visit_type_label)
    return f"{prefix}loan/{loan_application_id}/{agent_id}/{uuid.uuid4()}.{ext}"


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