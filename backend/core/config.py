"""
Application configuration
12-factor app principles: all config from environment variables
"""
import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # App configuration
    APP_NAME: str = "English Video Learning Platform"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "mysql://root:password@localhost:3306/english_video_learning"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Authentication
    JWT_SECRET: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # MinIO / S3
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET_VIDEOS: str = "videos"
    MINIO_BUCKET_SUBTITLES: str = "subtitles"
    MINIO_BUCKET_THUMBNAILS: str = "thumbnails"
    MINIO_BUCKET_AUDIO: str = "audio"
    MINIO_BUCKET_CLIPS: str = "clips"
    MINIO_USE_SSL: bool = False

    # AWS S3 (Production)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""
    USE_AWS_S3: bool = False  # True for production, False for local MinIO

    # Celery
    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672/"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # AI Services
    GEMINI_API_KEY: str = ""
    WHISPERX_API_URL: str = "http://localhost:8001"
    SEMANTIC_CHUNKER_URL: str = "http://localhost:8002"
    SMART_CLIPPER_URL: str = "http://localhost:8003"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_TRANSCRIPTS: str = "video_transcripts"

    # Rate Limiting
    RATE_LIMIT_FREE_CLIPS_PER_DAY: int = 5
    RATE_LIMIT_PREMIUM_CLIPS_PER_DAY: int = 999

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Monitoring
    SENTRY_DSN: str = ""
    DATADOG_API_KEY: str = ""

    # Payment (Stripe)
    STRIPE_PUBLIC_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
