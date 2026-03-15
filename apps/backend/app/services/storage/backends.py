"""
Storage Backends

Abstract base class and implementations for different storage backends.
"""

import abc
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class StorageBackend(abc.ABC):
    """
    Abstract base class for storage backends

    All storage backends must implement these methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize storage backend

        Args:
            config: Backend configuration
        """
        self.config = config
        self.backend_type = config.get("backend_type", "unknown")

    @abc.abstractmethod
    async def upload(
        self,
        file_path: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Upload a file to storage

        Args:
            file_path: Destination file path
            data: File data
            content_type: MIME type
            metadata: Additional metadata

        Returns:
            Upload result with file info
        """
        pass

    @abc.abstractmethod
    async def download(self, file_path: str) -> bytes:
        """
        Download a file from storage

        Args:
            file_path: Source file path

        Returns:
            File data
        """
        pass

    @abc.abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        Delete a file from storage

        Args:
            file_path: File path to delete

        Returns:
            True if successful
        """
        pass

    @abc.abstractmethod
    async def exists(self, file_path: str) -> bool:
        """
        Check if a file exists

        Args:
            file_path: File path to check

        Returns:
            True if file exists
        """
        pass

    @abc.abstractmethod
    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get file information

        Args:
            file_path: File path

        Returns:
            File information or None
        """
        pass

    @abc.abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List files in storage

        Args:
            prefix: Path prefix to filter
            limit: Maximum number of results
            continuation_token: Pagination token

        Returns:
            List result with files and continuation token
        """
        pass

    @abc.abstractmethod
    async def get_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        operation: str = "read",
    ) -> str:
        """
        Generate a signed URL for file access

        Args:
            file_path: File path
            expires_in: URL expiration in seconds
            operation: Operation type (read, write, delete)

        Returns:
            Signed URL
        """
        pass

    @abc.abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check backend health

        Returns:
            Health check result
        """
        pass

    def compute_checksum(self, data: bytes, algorithm: str = "sha256") -> str:
        """
        Compute file checksum

        Args:
            data: File data
            algorithm: Hash algorithm

        Returns:
            Checksum hex string
        """
        if algorithm == "md5":
            return hashlib.md5(data).hexdigest()
        elif algorithm == "sha256":
            return hashlib.sha256(data).hexdigest()
        elif algorithm == "sha1":
            return hashlib.sha1(data).hexdigest()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")


class S3StorageBackend(StorageBackend):
    """
    AWS S3 storage backend

    Uses boto3 for S3 operations.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bucket = config.get("bucket")
        self.region = config.get("region", "us-east-1")
        self.endpoint = config.get("endpoint")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self._client = None

    @property
    def client(self):
        """Lazy load boto3 client"""
        if self._client is None:
            try:
                import boto3
                from botocore.exceptions import ClientError

                config_dict = {
                    "region_name": self.region,
                }
                if self.endpoint:
                    config_dict["endpoint_url"] = self.endpoint

                self._client = boto3.client(
                    "s3",
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    **config_dict,
                )
            except ImportError:
                logger.warning("boto3 not installed, S3 backend unavailable")
                self._client = None

        return self._client

    async def upload(
        self,
        file_path: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload file to S3"""
        if not self.client:
            raise RuntimeError("S3 client not available")

        checksum = self.compute_checksum(data)

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = metadata

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=file_path,
                Body=data,
                **extra_args,
            )

            return {
                "file_path": file_path,
                "file_size": len(data),
                "checksum": checksum,
                "checksum_algorithm": "sha256",
            }
        except Exception as e:
            logger.error(f"S3 upload error: {e}")
            raise

    async def download(self, file_path: str) -> bytes:
        """Download file from S3"""
        if not self.client:
            raise RuntimeError("S3 client not available")

        try:
            response = self.client.get_object(Bucket=self.bucket, Key=file_path)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"S3 download error: {e}")
            raise

    async def delete(self, file_path: str) -> bool:
        """Delete file from S3"""
        if not self.client:
            raise RuntimeError("S3 client not available")

        try:
            self.client.delete_object(Bucket=self.bucket, Key=file_path)
            return True
        except Exception as e:
            logger.error(f"S3 delete error: {e}")
            return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in S3"""
        if not self.client:
            return False

        try:
            self.client.head_object(Bucket=self.bucket, Key=file_path)
            return True
        except:
            return False

    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file info from S3"""
        if not self.client:
            return None

        try:
            response = self.client.head_object(Bucket=self.bucket, Key=file_path)
            return {
                "file_path": file_path,
                "file_size": response.get("ContentLength", 0),
                "content_type": response.get("ContentType"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag", "").strip('"'),
            }
        except Exception as e:
            logger.error(f"S3 get file info error: {e}")
            return None

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files in S3"""
        if not self.client:
            return {"files": [], "common_prefixes": [], "is_truncated": False}

        try:
            args = {
                "Bucket": self.bucket,
                "Prefix": prefix,
                "MaxKeys": limit,
            }
            if continuation_token:
                args["ContinuationToken"] = continuation_token

            response = self.client.list_objects_v2(**args)

            files = []
            for obj in response.get("Contents", []):
                files.append({
                    "file_path": obj["Key"],
                    "file_size": obj["Size"],
                    "last_modified": obj["LastModified"],
                    "etag": obj["ETag"].strip('"') if "ETag" in obj else None,
                })

            return {
                "files": files,
                "common_prefixes": response.get("CommonPrefixes", []),
                "is_truncated": response.get("IsTruncated", False),
                "continuation_token": response.get("NextContinuationToken"),
            }
        except Exception as e:
            logger.error(f"S3 list files error: {e}")
            return {"files": [], "common_prefixes": [], "is_truncated": False}

    async def get_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        operation: str = "read",
    ) -> str:
        """Generate presigned URL for S3"""
        if not self.client:
            raise RuntimeError("S3 client not available")

        from botocore.exceptions import ClientError

        try:
            if operation == "read":
                url = self.client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": file_path},
                    ExpiresIn=expires_in,
                )
            elif operation == "write":
                url = self.client.generate_presigned_url(
                    "put_object",
                    Params={"Bucket": self.bucket, "Key": file_path},
                    ExpiresIn=expires_in,
                )
            else:
                raise ValueError(f"Unsupported operation: {operation}")

            return url
        except ClientError as e:
            logger.error(f"S3 presigned URL error: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check S3 health"""
        start = datetime.now()
        try:
            if not self.client:
                return {
                    "is_healthy": False,
                    "error": "S3 client not available",
                }

            # Try to list objects (limit to 1)
            self.client.list_objects_v2(Bucket=self.bucket, MaxKeys=1)

            latency = (datetime.now() - start).total_seconds() * 1000

            return {
                "is_healthy": True,
                "latency_ms": latency,
            }
        except Exception as e:
            return {
                "is_healthy": False,
                "error": str(e),
            }


class MinIOStorageBackend(S3StorageBackend):
    """
    MinIO storage backend

    Uses S3-compatible API with MinIO endpoint.
    """

    def __init__(self, config: Dict[str, Any]):
        # Override backend type
        config["backend_type"] = "minio"
        super().__init__(config)


class OSSStorageBackend(StorageBackend):
    """
    Aliyun OSS storage backend

    Uses oss2 for OSS operations.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.endpoint = config.get("oss_endpoint")
        self.bucket = config.get("oss_bucket")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self._client = None

    @property
    def client(self):
        """Lazy load oss2 client"""
        if self._client is None:
            try:
                import oss2

                auth = oss2.Auth(self.access_key, self.secret_key)
                self._client = oss2.Bucket(auth, self.endpoint, self.bucket)
            except ImportError:
                logger.warning("oss2 not installed, OSS backend unavailable")
                self._client = None

        return self._client

    async def upload(
        self,
        file_path: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload file to OSS"""
        if not self.client:
            raise RuntimeError("OSS client not available")

        checksum = self.compute_checksum(data)

        try:
            self.client.put_object(file_path, data)

            return {
                "file_path": file_path,
                "file_size": len(data),
                "checksum": checksum,
                "checksum_algorithm": "sha256",
            }
        except Exception as e:
            logger.error(f"OSS upload error: {e}")
            raise

    async def download(self, file_path: str) -> bytes:
        """Download file from OSS"""
        if not self.client:
            raise RuntimeError("OSS client not available")

        try:
            return self.client.get_object(file_path).read()
        except Exception as e:
            logger.error(f"OSS download error: {e}")
            raise

    async def delete(self, file_path: str) -> bool:
        """Delete file from OSS"""
        if not self.client:
            raise RuntimeError("OSS client not available")

        try:
            self.client.delete_object(file_path)
            return True
        except Exception as e:
            logger.error(f"OSS delete error: {e}")
            return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in OSS"""
        if not self.client:
            return False

        try:
            self.client.head_object(file_path)
            return True
        except:
            return False

    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file info from OSS"""
        if not self.client:
            return None

        try:
            info = self.client.head_object(file_path)
            return {
                "file_path": file_path,
                "file_size": info.content_length,
                "content_type": info.content_type,
                "last_modified": info.last_modified,
                "etag": info.etag,
            }
        except Exception as e:
            logger.error(f"OSS get file info error: {e}")
            return None

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files in OSS"""
        if not self.client:
            return {"files": [], "common_prefixes": [], "is_truncated": False}

        try:
            files = []
            for obj in oss2.ObjectIterator(self.client, prefix=prefix, max_keys=limit):
                files.append({
                    "file_path": obj.key,
                    "file_size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })

            return {
                "files": files,
                "common_prefixes": [],
                "is_truncated": False,
            }
        except Exception as e:
            logger.error(f"OSS list files error: {e}")
            return {"files": [], "common_prefixes": [], "is_truncated": False}

    async def get_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        operation: str = "read",
    ) -> str:
        """Generate signed URL for OSS"""
        if not self.client:
            raise RuntimeError("OSS client not available")

        try:
            url = self.client.sign_url("GET", file_path, expires_in)
            return url
        except Exception as e:
            logger.error(f"OSS signed URL error: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check OSS health"""
        start = datetime.now()
        try:
            if not self.client:
                return {
                    "is_healthy": False,
                    "error": "OSS client not available",
                }

            # Try to get bucket info
            self.client.get_bucket_info()

            latency = (datetime.now() - start).total_seconds() * 1000

            return {
                "is_healthy": True,
                "latency_ms": latency,
            }
        except Exception as e:
            return {
                "is_healthy": False,
                "error": str(e),
            }


class NFSStorageBackend(StorageBackend):
    """
    NFS storage backend

    Uses local filesystem with NFS mount.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mount_path = config.get("mount_path", "/mnt/nfs")
        self.nfs_server = config.get("nfs_server")
        self.nfs_path = config.get("nfs_path")

    def _get_full_path(self, file_path: str) -> str:
        """Get full filesystem path"""
        return os.path.join(self.mount_path, file_path.lstrip("/"))

    async def upload(
        self,
        file_path: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload file to NFS"""
        full_path = self._get_full_path(file_path)

        # Create directory if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(data)

        checksum = self.compute_checksum(data)

        return {
            "file_path": file_path,
            "file_size": len(data),
            "checksum": checksum,
            "checksum_algorithm": "sha256",
        }

    async def download(self, file_path: str) -> bytes:
        """Download file from NFS"""
        full_path = self._get_full_path(file_path)

        with open(full_path, "rb") as f:
            return f.read()

    async def delete(self, file_path: str) -> bool:
        """Delete file from NFS"""
        full_path = self._get_full_path(file_path)

        try:
            os.remove(full_path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"NFS delete error: {e}")
            return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in NFS"""
        full_path = self._get_full_path(file_path)
        return os.path.exists(full_path)

    async def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file info from NFS"""
        full_path = self._get_full_path(file_path)

        try:
            stat = os.stat(full_path)
            return {
                "file_path": file_path,
                "file_size": stat.st_size,
                "last_modified": datetime.fromtimestamp(stat.st_mtime),
            }
        except FileNotFoundError:
            return None

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files in NFS"""
        full_path = self._get_full_path(prefix)

        try:
            files = []
            count = 0

            for root, dirs, filenames in os.walk(full_path):
                for filename in filenames:
                    if count >= limit:
                        return {
                            "files": files,
                            "common_prefixes": [],
                            "is_truncated": True,
                        }

                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, self.mount_path)

                    stat = os.stat(file_path)
                    files.append({
                        "file_path": rel_path,
                        "file_size": stat.st_size,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime),
                    })
                    count += 1

            return {
                "files": files,
                "common_prefixes": [],
                "is_truncated": False,
            }
        except Exception as e:
            logger.error(f"NFS list files error: {e}")
            return {"files": [], "common_prefixes": [], "is_truncated": False}

    async def get_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600,
        operation: str = "read",
    ) -> str:
        """Generate signed URL for NFS (not applicable)"""
        raise NotImplementedError("Signed URLs not supported for NFS backend")

    async def health_check(self) -> Dict[str, Any]:
        """Check NFS health"""
        start = datetime.now()
        try:
            # Check if mount path exists and is accessible
            if not os.path.exists(self.mount_path):
                return {
                    "is_healthy": False,
                    "error": f"Mount path {self.mount_path} does not exist",
                }

            # Try to list directory
            os.listdir(self.mount_path)

            latency = (datetime.now() - start).total_seconds() * 1000

            return {
                "is_healthy": True,
                "latency_ms": latency,
            }
        except Exception as e:
            return {
                "is_healthy": False,
                "error": str(e),
            }


class LocalStorageBackend(NFSStorageBackend):
    """
    Local storage backend

    Uses local filesystem.
    """

    def __init__(self, config: Dict[str, Any]):
        config["backend_type"] = "local"
        config["mount_path"] = config.get("mount_path", "/tmp/storage")
        super().__init__(config)


def get_storage_backend(config: Dict[str, Any]) -> StorageBackend:
    """
    Get storage backend instance based on configuration

    Args:
        config: Backend configuration

    Returns:
        Storage backend instance
    """
    backend_type = config.get("backend_type", "local").lower()

    if backend_type == "s3":
        return S3StorageBackend(config)
    elif backend_type == "minio":
        return MinIOStorageBackend(config)
    elif backend_type == "oss":
        return OSSStorageBackend(config)
    elif backend_type == "nfs":
        return NFSStorageBackend(config)
    elif backend_type == "local":
        return LocalStorageBackend(config)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")
