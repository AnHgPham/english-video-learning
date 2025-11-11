"""
Subtitles API endpoints
MODULE 2 & 3: Video subtitles and transcript management
Handles subtitle retrieval and admin editing
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from core.database import get_db
from core.security import get_current_user, get_current_admin
from models.user import User
from models.video import Video, Subtitle, SubtitleSource
from models.transcript import TranscriptSentence

router = APIRouter()


# ============================================
# Request/Response Models (Pydantic schemas)
# ============================================

class SubtitleResponse(BaseModel):
    """Subtitle track information"""
    id: int
    videoId: int
    language: str
    languageName: str
    subtitleUrl: str
    subtitleKey: str
    isDefault: int
    source: str
    createdAt: str
    updatedAt: str


class SubtitleListResponse(BaseModel):
    """List of subtitle tracks for a video"""
    videoId: int
    videoTitle: str
    subtitles: List[SubtitleResponse]


class SubtitleContentItem(BaseModel):
    """Individual subtitle entry with timing"""
    index: int
    startTime: float
    endTime: float
    text: str


class SubtitleContentResponse(BaseModel):
    """Complete subtitle content (SRT/VTT format data)"""
    videoId: int
    language: str
    languageName: str
    items: List[SubtitleContentItem]
    format: str  # "srt", "vtt", or "json"


class EditSubtitleRequest(BaseModel):
    """Request to edit subtitle content (admin only)"""
    sentence_id: int = Field(..., description="Transcript sentence ID to edit")
    new_text: str = Field(..., min_length=1, max_length=5000, description="New text content")
    start_time: Optional[float] = Field(None, ge=0, description="New start time (seconds)")
    end_time: Optional[float] = Field(None, ge=0, description="New end time (seconds)")


class TranscriptSentenceResponse(BaseModel):
    """Transcript sentence for editing"""
    id: int
    transcriptId: int
    videoId: int
    sentenceIndex: int
    text: str
    startTime: float
    endTime: float
    words: Optional[dict]
    createdAt: str


# ============================================
# Subtitle Endpoints (Public)
# ============================================

@router.get("/{video_id}", response_model=SubtitleListResponse)
async def get_video_subtitles(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all subtitle tracks for a video

    Returns list of available subtitle languages with download URLs.
    Frontend can use this to populate subtitle selector in video player.

    **Parameters**:
    - **video_id**: ID of the video

    **Returns**:
    - List of subtitle tracks with metadata and URLs
    """
    # Verify video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Get all subtitles for this video
    subtitles = db.query(Subtitle).filter(
        Subtitle.video_id == video_id
    ).order_by(Subtitle.is_default.desc(), Subtitle.language).all()

    if not subtitles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subtitles found for this video"
        )

    # Build response
    subtitle_items = [
        SubtitleResponse(
            id=sub.id,
            videoId=sub.video_id,
            language=sub.language,
            languageName=sub.language_name,
            subtitleUrl=sub.subtitle_url,
            subtitleKey=sub.subtitle_key,
            isDefault=sub.is_default,
            source=sub.source.value,
            createdAt=sub.created_at.isoformat() if sub.created_at else None,
            updatedAt=sub.updated_at.isoformat() if sub.updated_at else None
        )
        for sub in subtitles
    ]

    return SubtitleListResponse(
        videoId=video.id,
        videoTitle=video.title,
        subtitles=subtitle_items
    )


@router.get("/{video_id}/content", response_model=SubtitleContentResponse)
async def get_subtitle_content(
    video_id: int,
    language: str = Query("en", description="Subtitle language code (e.g., 'en', 'vi')"),
    format: str = Query("json", description="Response format: 'json', 'srt', or 'vtt'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get subtitle content for a video in specified format

    **Note**: For production, subtitle files (SRT/VTT) should be served directly from S3/MinIO.
    This endpoint is useful for:
    - Getting structured JSON subtitle data
    - Format conversion (if needed)
    - Real-time editing previews

    **Parameters**:
    - **video_id**: ID of the video
    - **language**: Subtitle language code (default: "en")
    - **format**: Response format - "json" (default), "srt", or "vtt"

    **Returns**:
    - Subtitle content with timing information
    """
    # Verify video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Get subtitle track
    subtitle = db.query(Subtitle).filter(
        Subtitle.video_id == video_id,
        Subtitle.language == language
    ).first()

    if not subtitle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No subtitle found for language '{language}'"
        )

    # Get transcript sentences (generated by AI pipeline)
    sentences = db.query(TranscriptSentence).filter(
        TranscriptSentence.video_id == video_id
    ).order_by(TranscriptSentence.sentence_index).all()

    if not sentences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcript data available for this video"
        )

    # Build subtitle items
    items = [
        SubtitleContentItem(
            index=sent.sentence_index,
            startTime=sent.start_time,
            endTime=sent.end_time,
            text=sent.text
        )
        for sent in sentences
    ]

    # TODO: For SRT/VTT format, generate proper formatted string
    # For now, return JSON format regardless of request
    if format in ["srt", "vtt"]:
        # In production, convert to SRT/VTT format string
        pass

    return SubtitleContentResponse(
        videoId=video.id,
        language=subtitle.language,
        languageName=subtitle.language_name,
        items=items,
        format="json"
    )


@router.get("/{video_id}/download/{language}")
async def download_subtitle_file(
    video_id: int,
    language: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get direct download link for subtitle file

    Returns a redirect to the S3/MinIO URL or a pre-signed URL for download.

    **Parameters**:
    - **video_id**: ID of the video
    - **language**: Subtitle language code

    **Returns**:
    - Redirect to subtitle file URL
    """
    from fastapi.responses import RedirectResponse

    # Get subtitle
    subtitle = db.query(Subtitle).filter(
        Subtitle.video_id == video_id,
        Subtitle.language == language
    ).first()

    if not subtitle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No subtitle found for language '{language}'"
        )

    # In production, generate pre-signed URL if using private S3 bucket
    # For now, redirect to public URL
    return RedirectResponse(url=subtitle.subtitle_url)


# ============================================
# Admin Subtitle Editing Endpoints
# ============================================

@router.get("/admin/{video_id}/sentences", response_model=List[TranscriptSentenceResponse])
async def get_transcript_sentences_for_editing(
    video_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get transcript sentences for editing (Admin only)

    Returns paginated list of transcript sentences that can be edited.
    Used in admin dashboard for subtitle correction.

    **Parameters**:
    - **video_id**: ID of the video
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 200)

    **Returns**:
    - List of transcript sentences with edit capabilities
    """
    # Verify video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Get total count
    total = db.query(TranscriptSentence).filter(
        TranscriptSentence.video_id == video_id
    ).count()

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcript data found for this video"
        )

    # Get paginated sentences
    offset = (page - 1) * page_size
    sentences = db.query(TranscriptSentence).filter(
        TranscriptSentence.video_id == video_id
    ).order_by(TranscriptSentence.sentence_index).offset(offset).limit(page_size).all()

    # Build response
    return [
        TranscriptSentenceResponse(
            id=sent.id,
            transcriptId=sent.transcript_id,
            videoId=sent.video_id,
            sentenceIndex=sent.sentence_index,
            text=sent.text,
            startTime=sent.start_time,
            endTime=sent.end_time,
            words=sent.words,
            createdAt=sent.created_at.isoformat() if sent.created_at else None
        )
        for sent in sentences
    ]


@router.patch("/admin/sentence/{id}", response_model=TranscriptSentenceResponse)
async def edit_transcript_sentence(
    id: int,
    request: EditSubtitleRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Edit a transcript sentence (Admin only)

    Allows admins to correct AI-generated transcripts.
    Changes are reflected in subtitles and search results.

    **Important**: After editing, consider:
    - Regenerating subtitle files (SRT/VTT)
    - Re-indexing in Elasticsearch
    - Invalidating cached data

    **Parameters**:
    - **id**: Transcript sentence ID
    - **new_text**: Corrected text
    - **start_time**: Corrected start time (optional)
    - **end_time**: Corrected end time (optional)

    **Returns**:
    - Updated transcript sentence
    """
    # Find sentence
    sentence = db.query(TranscriptSentence).filter(
        TranscriptSentence.id == id
    ).first()

    if not sentence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript sentence not found"
        )

    # Validate timing if provided
    if request.start_time is not None and request.end_time is not None:
        if request.start_time >= request.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time must be less than end_time"
            )

    # Update sentence
    sentence.text = request.new_text

    if request.start_time is not None:
        sentence.start_time = request.start_time

    if request.end_time is not None:
        sentence.end_time = request.end_time

    db.commit()
    db.refresh(sentence)

    # TODO: Trigger subtitle file regeneration
    # TODO: Update Elasticsearch index
    # TODO: Clear relevant caches

    return TranscriptSentenceResponse(
        id=sentence.id,
        transcriptId=sentence.transcript_id,
        videoId=sentence.video_id,
        sentenceIndex=sentence.sentence_index,
        text=sentence.text,
        startTime=sentence.start_time,
        endTime=sentence.end_time,
        words=sentence.words,
        createdAt=sentence.created_at.isoformat() if sentence.created_at else None
    )


@router.delete("/admin/sentence/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcript_sentence(
    id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a transcript sentence (Admin only)

    Use with caution - this permanently removes a sentence from the transcript.
    Useful for removing incorrectly detected segments or artifacts.

    **Parameters**:
    - **id**: Transcript sentence ID
    """
    # Find sentence
    sentence = db.query(TranscriptSentence).filter(
        TranscriptSentence.id == id
    ).first()

    if not sentence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript sentence not found"
        )

    # Store video_id for cleanup
    video_id = sentence.video_id

    # Delete sentence
    db.delete(sentence)
    db.commit()

    # TODO: Re-index remaining sentences
    # TODO: Regenerate subtitle file
    # TODO: Update Elasticsearch

    return None


@router.post("/admin/{video_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
async def regenerate_subtitle_files(
    video_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Regenerate subtitle files from transcript data (Admin only)

    Use after editing transcript sentences to update subtitle files.
    This will:
    1. Generate new SRT/VTT files from transcript sentences
    2. Upload to S3/MinIO
    3. Update subtitle records with new URLs

    **Parameters**:
    - **video_id**: ID of the video

    **Returns**:
    - Accepted status (processing in background)
    """
    # Verify video exists
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Verify transcript exists
    sentences = db.query(TranscriptSentence).filter(
        TranscriptSentence.video_id == video_id
    ).count()

    if sentences == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No transcript data found for this video"
        )

    # TODO: Queue background job to regenerate subtitle files
    # - Generate SRT/VTT format from transcript sentences
    # - Upload to S3/MinIO
    # - Update Subtitle records

    return {
        "message": "Subtitle regeneration queued",
        "videoId": video_id,
        "status": "processing"
    }
