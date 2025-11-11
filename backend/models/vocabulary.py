"""
Vocabulary model - User saved words
MODULE 5: Vocabulary Management
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from .base import Base


class UserVocabulary(Base):
    """
    User's saved vocabulary from videos
    Tracks learning progress and context
    """
    __tablename__ = "user_vocabulary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column("userId", Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Vocabulary information
    word = Column(String(200), nullable=False)
    translation = Column(Text, nullable=True)  # Vietnamese translation
    phonetic = Column(String(100), nullable=True)  # IPA phonetic
    definition = Column(Text, nullable=True)  # English definition
    example = Column(Text, nullable=True)  # Example sentence

    # Context from video
    video_id = Column("videoId", Integer, ForeignKey("videos.id"), nullable=True)
    timestamp = Column(Integer, nullable=True)  # Timestamp in video (seconds)
    context = Column(Text, nullable=True)  # Sentence containing the word

    # Learning progress
    mastery_level = Column("masteryLevel", Integer, default=0, nullable=False)  # 0-5 scale
    review_count = Column("reviewCount", Integer, default=0, nullable=False)
    last_reviewed_at = Column("lastReviewedAt", DateTime, nullable=True)

    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    video = relationship("Video")

    def __repr__(self):
        return f"<UserVocabulary(id={self.id}, user_id={self.user_id}, word={self.word})>"

    def to_dict(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "word": self.word,
            "translation": self.translation,
            "phonetic": self.phonetic,
            "definition": self.definition,
            "example": self.example,
            "videoId": self.video_id,
            "timestamp": self.timestamp,
            "context": self.context,
            "masteryLevel": self.mastery_level,
            "reviewCount": self.review_count,
            "lastReviewedAt": self.last_reviewed_at.isoformat() if self.last_reviewed_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
