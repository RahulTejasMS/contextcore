import boto3
from botocore.client import Config
from app.core.config import settings

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

def download_file_from_s3(s3_key: str) -> bytes:
    """Downloads a file from MinIO/S3 and returns its bytes."""
    client = get_s3_client()
    response = client.get_object(
        Bucket=settings.minio_bucket,
        Key=s3_key
    )
    return response["Body"].read()