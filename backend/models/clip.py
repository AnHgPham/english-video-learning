"""
Clip models - User-generated video clips and quota tracking
MODULE 7: Search & Clip Management
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Enum as SQLEnum, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date
import enum

from .base import Base


class ClipStatus(str, enum.Enum):
    """Clip processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Clip(Base):
    """
    User-generated video clips from search results
    Created by the Smart Clipper + FFMPEG pipeline
    """
    __tablename__ = "clips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("userId", Integer, ForeignKey("users.id"), nullable=False, index=True)
    video_id = Column("videoId", Integer, ForeignKey("videos.id"), nullable=False, index=True)

    # Clip metadata
    title = Column(String(255), nullable=True)
    search_phrase = Column("searchPhrase", String(500), nullable=True)  # Original search phrase

    # Timing (determined by Smart Clipper AI)
    start_time = Column("startTime", Float, nullable=False)  # Start timestamp (seconds)
    end_time = Column("endTime", Float, nullable=False)  # End timestamp (seconds)
    duration = Column(Integer, nullable=True)  # Duration in seconds

    # Clip file on S3/MinIO
    clip_url = Column("clipUrl", Text, nullable=True)
    clip_key = Column("clipKey", String(500), nullable=True)
    thumbnail_url = Column("thumbnailUrl", Text, nullable=True)

    # Subtitle for this clip
    subtitle_url = Column("subtitleUrl", Text, nullable=True)
    subtitle_key = Column("subtitleKey", String(500), nullable=True)

    # Status
    status = Column(SQLEnum(ClipStatus), default=ClipStatus.PENDING, nullable=False)
    error_message = Column("errorMessage", Text, nullable=True)

    # Visibility
    is_public = Column("isPublic", Integer, default=0, nullable=False)  # 0 = private, 1 = public

    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column("completedAt", DateTime, nullable=True)

    # Relationships
    user = relationship("User")
    video = relationship("Video")

    def __repr__(self):
        return f"<Clip(id={self.id}, user_id={self.user_id}, status={self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "videoId": self.video_id,
            "title": self.title,
            "searchPhrase": self.search_phrase,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "duration": self.duration,
            "clipUrl": self.clip_url,
            "clipKey": self.clip_key,
            "thumbnailUrl": self.thumbnail_url,
            "subtitleUrl": self.subtitle_url,
            "subtitleKey": self.subtitle_key,
            "status": self.status.value,
            "errorMessage": self.error_message,
            "isPublic": self.is_public,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
        }


class UserQuota(Base):
    """
    Daily clip generation quota for users
    Free: 5 clips/day, Premium: unlimited
    """
    __tablename__ = "user_quota"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("userId", Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Quota tracking
    quota_date = Column("quotaDate", Date, default=date.today, nullable=False, index=True)
    clips_created = Column("clipsCreated", Integer, default=0, nullable=False)
    max_clips = Column("maxClips", Integer, default=5, nullable=False)  # 5 for free, 999 for premium

    # Premium status
    is_premium = Column("isPremium", Integer, default=0, nullable=False)  # 0 = free, 1 = premium

    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<UserQuota(user_id={self.user_id}, date={self.quota_date}, used={self.clips_created}/{self.max_clips})>"

    def has_quota_remaining(self) -> bool:
        """Check if user has clips remaining for today"""
        return self.clips_created < self.max_clips

    def increment_usage(self):
        """Increment clips created counter"""
        self.clips_created += 1

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "quotaDate": self.quota_date.isoformat() if self.quota_date else None,
            "clipsCreated": self.clips_created,
            "maxClips": self.max_clips,
            "remaining": max(0, self.max_clips - self.clips_created),
            "isPremium": self.is_premium,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
