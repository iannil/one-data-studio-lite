#!/usr/bin/env python3
"""
MLflow Initialization Script

Creates the MLflow database and configures MinIO bucket.
Run this after starting the MLflow service.
"""

import os
import time
import logging
from sqlalchemy import create_engine, text
from minio import Minio
from minio.error import S3Error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mlflow_database():
    """Create MLflow database in PostgreSQL"""
    pg_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@postgres:5432/postgres"
    )

    engine = create_engine(pg_url.replace("smart_data", "postgres"))

    try:
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname='mlflow'")
            )
            if not result.fetchone():
                conn.execute(text("COMMIT"))
                conn.execute(text("CREATE DATABASE mlflow"))
                conn.execute(text("COMMIT"))
                logger.info("Created MLflow database")
            else:
                logger.info("MLflow database already exists")
    except Exception as e:
        logger.error(f"Failed to create MLflow database: {e}")
        raise


def create_minio_buckets():
    """Create MinIO buckets for MLflow"""
    minio_endpoint = os.getenv(
        "MINIO_ENDPOINT",
        "minio:9000"
    )
    minio_access = os.getenv("MINIO_ROOT_USER", "minioadmin")
    minio_secret = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

    client = Minio(
        minio_endpoint,
        access_key=minio_access,
        secret_key=minio_secret,
        secure=False
    )

    buckets = ["mlflow", "models", "datasets", "artifacts"]

    for bucket in buckets:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")

                # Set bucket policy for public read (optional)
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket}/*"]
                        }
                    ]
                }
                # client.set_bucket_policy(bucket, json.dumps(policy))
            else:
                logger.info(f"Bucket already exists: {bucket}")
        except S3Error as e:
            logger.error(f"Failed to create bucket {bucket}: {e}")


def main():
    """Initialize MLflow environment"""
    logger.info("Initializing MLflow environment...")

    # Wait for PostgreSQL to be ready
    logger.info("Waiting for PostgreSQL...")
    time.sleep(5)

    # Create MLflow database
    create_mlflow_database()

    # Wait for MinIO to be ready
    logger.info("Waiting for MinIO...")
    time.sleep(5)

    # Create MinIO buckets
    create_minio_buckets()

    logger.info("MLflow initialization complete!")


if __name__ == "__main__":
    main()
