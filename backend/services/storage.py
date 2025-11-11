"""
Storage Service - MinIO/S3 integration
Handles file uploads, downloads, and presigned URLs
"""
import os
from typing import Optional, BinaryIO
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
import boto3
from botocore.exceptions import ClientError

from core.config import settings


class StorageService:
    """
    Storage service supporting both MinIO (local) and AWS S3 (production)
    Automatically switches based on USE_AWS_S3 setting
    """

    def __init__(self):
        self.use_aws = settings.USE_AWS_S3

        if self.use_aws:
            # AWS S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        else:
            # MinIO client (S3-compatible)
            self.minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_USE_SSL
            )

    def _ensure_bucket_exists(self, bucket_name: str):
        """Ensure bucket exists (MinIO only)"""
        if not self.use_aws:
            try:
                if not self.minio_client.bucket_exists(bucket_name):
                    self.minio_client.make_bucket(bucket_name)
                    print(f"✅ Created bucket: {bucket_name}")
            except S3Error as e:
                print(f"⚠️ Error ensuring bucket exists: {e}")

    def upload_file(
        self,
        file_data: BinaryIO,
        object_key: str,
        bucket_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload file to storage

        Args:
            file_data: File object or bytes
            object_key: S3 object key (path in bucket)
            bucket_name: Bucket name
            content_type: MIME type

        Returns:
            URL of uploaded file
        """
        try:
            if self.use_aws:
                # AWS S3 upload
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    object_key,
                    ExtraArgs={'ContentType': content_type}
                )
                url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{object_key}"
            else:
                # MinIO upload
                self._ensure_bucket_exists(bucket_name)

                # Get file size
                file_data.seek(0, 2)  # Seek to end
                file_size = file_data.tell()
                file_data.seek(0)  # Reset to beginning

                self.minio_client.put_object(
                    bucket_name,
                    object_key,
                    file_data,
                    length=file_size,
                    content_type=content_type
                )

                # Construct URL
                url = f"http://{settings.MINIO_ENDPOINT}/{bucket_name}/{object_key}"

            return url

        except (S3Error, ClientError) as e:
            raise Exception(f"Failed to upload file: {str(e)}")

    def upload_file_from_path(
        self,
        file_path: str,
        object_key: str,
        bucket_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload file from local path

        Args:
            file_path: Path to local file
            object_key: S3 object key
            bucket_name: Bucket name
            content_type: MIME type

        Returns:
            URL of uploaded file
        """
        with open(file_path, 'rb') as file_data:
            return self.upload_file(file_data, object_key, bucket_name, content_type)

    def get_presigned_url(
        self,
        object_key: str,
        bucket_name: str,
        expires_in: int = 3600
    ) -> str:
        """
        Generate presigned URL for temporary access

        Args:
            object_key: S3 object key
            bucket_name: Bucket name
            expires_in: Expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL
        """
        try:
            if self.use_aws:
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': object_key
                    },
                    ExpiresIn=expires_in
                )
            else:
                url = self.minio_client.presigned_get_object(
                    bucket_name,
                    object_key,
                    expires=timedelta(seconds=expires_in)
                )

            return url

        except (S3Error, ClientError) as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    def delete_file(self, object_key: str, bucket_name: str):
        """
        Delete file from storage

        Args:
            object_key: S3 object key
            bucket_name: Bucket name
        """
        try:
            if self.use_aws:
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
            else:
                self.minio_client.remove_object(bucket_name, object_key)

        except (S3Error, ClientError) as e:
            raise Exception(f"Failed to delete file: {str(e)}")

    def file_exists(self, object_key: str, bucket_name: str) -> bool:
        """
        Check if file exists in storage

        Args:
            object_key: S3 object key
            bucket_name: Bucket name

        Returns:
            True if file exists, False otherwise
        """
        try:
            if self.use_aws:
                self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
            else:
                self.minio_client.stat_object(bucket_name, object_key)
            return True
        except:
            return False


# Global storage service instance
storage_service = StorageService()
