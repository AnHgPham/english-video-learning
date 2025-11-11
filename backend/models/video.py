"""
Video management models - Videos, Categories, Subtitles
MODULE 2: Video Management Tables
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .base import Base


class VideoLevel(str, enum.Enum):
    """English proficiency levels"""
    A1 = "A1"  # Beginner
    A2 = "A2"  # Elementary
    B1 = "B1"  # Intermediate
    B2 = "B2"  # Upper Intermediate
    C1 = "C1"  # Advanced
    C2 = "C2"  # Proficiency


class VideoStatus(str, enum.Enum):
    """Video processing status"""
    DRAFT = "draft"
    PROCESSING = "processing"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SubtitleSource(str, enum.Enum):
    """Source of subtitle"""
    MANUAL = "manual"
    AI_GENERATED = "ai_generated"
    IMPORTED = "imported"


class Category(Base):
    """
    Video categories (Movies, Lectures, Podcasts, etc.)
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)

    # Relationships
    videos = relationship("Video", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class Video(Base):
    """
    Video metadata and storage information
    Each video can have multiple subtitles and belongs to a category
    """
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Basic information
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Video file on S3/MinIO
    video_url = Column("videoUrl", Text, nullable=False)
    video_key = Column("videoKey", String(500), nullable=False)
    thumbnail_url = Column("thumbnailUrl", Text, nullable=True)
    thumbnail_key = Column("thumbnailKey", String(500), nullable=True)

    # Audio file (extracted by pipeline)
    audio_url = Column("audioUrl", Text, nullable=True)
    audio_key = Column("audioKey", String(500), nullable=True)

    # Metadata
    duration = Column(Integer, nullable=True)  # Duration in seconds
    resolution = Column(String(20), nullable=True)  # e.g., "1920x1080"
    level = Column(SQLEnum(VideoLevel), nullable=False)
    language = Column(String(10), default="en", nullable=False)

    # Relationships
    category_id = Column("categoryId", Integer, ForeignKey("categories.id"), nullable=True)
    uploaded_by = Column("uploadedBy", Integer, ForeignKey("users.id"), nullable=False)

    # Status
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.DRAFT, nullable=False)
    view_count = Column("viewCount", Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    published_at = Column("publishedAt", DateTime, nullable=True)

    # Relationships
    category = relationship("Category", back_populates="videos")
    uploader = relationship("User")
    subtitles = relationship("Subtitle", back_populates="video", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, title={self.title}, status={self.status})>"

    def to_dict(self, include_subtitles=False):
        data = {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "description": self.description,
            "videoUrl": self.video_url,
            "videoKey": self.video_key,
            "thumbnailUrl": self.thumbnail_url,
            "duration": self.duration,
            "level": self.level.value,
            "language": self.language,
            "categoryId": self.category_id,
            "uploadedBy": self.uploaded_by,
            "status": self.status.value,
            "viewCount": self.view_count,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "publishedAt": self.published_at.isoformat() if self.published_at else None,
        }

        if include_subtitles and self.subtitles:
            data["subtitles"] = [sub.to_dict() for sub in self.subtitles]

        return data


class Subtitle(Base):
    """
    Subtitle files for videos (multilingual support)
    Each video can have multiple subtitle tracks
    """
    __tablename__ = "subtitles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column("videoId", Integer, ForeignKey("videos.id"), nullable=False)

    # Subtitle information
    language = Column(String(10), nullable=False)  # ISO 639-1 code (vi, en, zh, ja, etc.)
    language_name = Column("languageName", String(50), nullable=False)  # Vietnamese, English, etc.

    # Subtitle file on S3/MinIO
    subtitle_url = Column("subtitleUrl", Text, nullable=False)
    subtitle_key = Column("subtitleKey", String(500), nullable=False)

    # Metadata
    is_default = Column("isDefault", Integer, default=0, nullable=False)  # 1 = default subtitle
    source = Column(SQLEnum(SubtitleSource), default=SubtitleSource.MANUAL, nullable=False)

    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    video = relationship("Video", back_populates="subtitles")

    def __repr__(self):
        return f"<Subtitle(id={self.id}, video_id={self.video_id}, language={self.language})>"

    def to_dict(self):
        return {
            "id": self.id,
            "videoId": self.video_id,
            "language": self.language,
            "languageName": self.language_name,
            "subtitleUrl": self.subtitle_url,
            "subtitleKey": self.subtitle_key,
            "isDefault": self.is_default,
            "source": self.source.value,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
