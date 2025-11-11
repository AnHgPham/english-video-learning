"""
Transcript models - AI-generated transcripts and sentences
MODULE 2 Extension: AI Pipeline Results
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from .base import Base


class Transcript(Base):
    """
    AI-generated transcript for a video
    Stores raw WhisperX output and metadata
    """
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column("videoId", Integer, ForeignKey("videos.id"), nullable=False, unique=True)

    # Transcript metadata
    language = Column(String(10), default="en", nullable=False)
    source = Column(String(50), default="whisperx", nullable=False)  # whisperx, manual, etc.

    # Raw transcript data (JSON array of word-level timestamps)
    # Format: [{"word": "Hello", "start": 0.5, "end": 0.8, "score": 0.95}, ...]
    raw_data = Column("rawData", JSON, nullable=True)

    # Processing status
    is_processed = Column("isProcessed", Integer, default=0, nullable=False)  # 0 = raw, 1 = chunked

    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)
    updated_at = Column("updatedAt", DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    video = relationship("Video", back_populates="transcripts")
    sentences = relationship("TranscriptSentence", back_populates="transcript", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transcript(id={self.id}, video_id={self.video_id}, language={self.language})>"

    def to_dict(self, include_sentences=False):
        data = {
            "id": self.id,
            "videoId": self.video_id,
            "language": self.language,
            "source": self.source,
            "rawData": self.raw_data,
            "isProcessed": self.is_processed,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_sentences and self.sentences:
            data["sentences"] = [sent.to_dict() for sent in self.sentences]

        return data


class TranscriptSentence(Base):
    """
    Semantic-chunked sentences from transcript
    Created by the Semantic Chunker service
    """
    __tablename__ = "transcript_sentences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column("transcriptId", Integer, ForeignKey("transcripts.id"), nullable=False, index=True)
    video_id = Column("videoId", Integer, ForeignKey("videos.id"), nullable=False, index=True)

    # Sentence data
    sentence_index = Column("sentenceIndex", Integer, nullable=False)  # Order in transcript
    text = Column(Text, nullable=False)  # Complete sentence text

    # Timing
    start_time = Column("startTime", Float, nullable=False)  # Start timestamp (seconds)
    end_time = Column("endTime", Float, nullable=False)  # End timestamp (seconds)

    # Word-level data
    words = Column(JSON, nullable=True)  # Array of word objects with timestamps

    # Timestamps
    created_at = Column("createdAt", DateTime, default=func.now(), nullable=False)

    # Relationships
    transcript = relationship("Transcript", back_populates="sentences")
    video = relationship("Video")

    def __repr__(self):
        return f"<TranscriptSentence(id={self.id}, transcript_id={self.transcript_id}, text={self.text[:50]})>"

    def to_dict(self):
        return {
            "id": self.id,
            "transcriptId": self.transcript_id,
            "videoId": self.video_id,
            "sentenceIndex": self.sentence_index,
            "text": self.text,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "words": self.words,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
