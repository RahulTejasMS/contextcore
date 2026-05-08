# ============================================================
# storage.py — MinIO/S3 file operations
# ============================================================
import boto3
from botocore.client import Config
from app.core.config import settings

def get_s3_client():
    """
    Returns a boto3 S3 client pointed at MinIO.
    In production: remove endpoint_url and it points to AWS S3.
    """
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket_exists():
    """Creates the bucket if it doesn't exist yet."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.minio_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.minio_bucket)
        print(f"✅ Created bucket: {settings.minio_bucket}")


def upload_file_to_s3(file_bytes: bytes, s3_key: str, content_type: str) -> str:
    """
    Uploads a file to MinIO/S3.
    Returns the s3_key (the path of the file inside the bucket).
    """
    client = get_s3_client()
    client.put_object(
        Bucket=settings.minio_bucket,
        Key=s3_key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return s3_key


def generate_presigned_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    """
    Generates a temporary download URL for a file.
    Expires after expiry_seconds (default: 1 hour).
    """
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.minio_bucket, "Key": s3_key},
        ExpiresIn=expiry_seconds,
    )