"""
Clips API endpoints
MODULE 7: Smart Clipper - Video clip generation
Handles user clip requests with AI-powered smart clipping and quota management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.video import Video
from models.clip import Clip, ClipStatus, UserQuota

router = APIRouter()


# ============================================
# Request/Response Models (Pydantic schemas)
# ============================================

class CreateClipRequest(BaseModel):
    """Request to create a new clip"""
    video_id: int = Field(..., description="Video ID to create clip from")
    search_phrase: str = Field(..., min_length=1, max_length=500, description="Phrase to search for in transcript")
    title: Optional[str] = Field(None, max_length=255, description="Custom title for clip")

    # Optional manual timing override (if not using AI Smart Clipper)
    start_time: Optional[float] = Field(None, ge=0, description="Manual start time (seconds)")
    end_time: Optional[float] = Field(None, ge=0, description="Manual end time (seconds)")


class ClipResponse(BaseModel):
    """Clip information response"""
    id: int
    userId: int
    videoId: int
    title: Optional[str]
    searchPhrase: Optional[str]
    startTime: float
    endTime: float
    duration: Optional[int]
    clipUrl: Optional[str]
    clipKey: Optional[str]
    thumbnailUrl: Optional[str]
    subtitleUrl: Optional[str]
    status: str
    errorMessage: Optional[str]
    isPublic: int
    createdAt: str
    updatedAt: str
    completedAt: Optional[str]

    # Include video info
    videoTitle: Optional[str] = None
    videoThumbnailUrl: Optional[str] = None


class ClipListResponse(BaseModel):
    """List of clips with pagination"""
    items: List[ClipResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int


class ClipStatusResponse(BaseModel):
    """Clip processing status"""
    id: int
    status: str
    progress: Optional[int] = None  # 0-100 percentage
    errorMessage: Optional[str] = None
    clipUrl: Optional[str] = None
    estimatedTimeRemaining: Optional[int] = None  # seconds


class QuotaResponse(BaseModel):
    """User's daily clip quota"""
    userId: int
    quotaDate: str
    clipsCreated: int
    maxClips: int
    remaining: int
    isPremium: int
    nextResetAt: str  # ISO timestamp of next quota reset


# ============================================
# Helper Functions
# ============================================

def get_or_create_quota(db: Session, user: User) -> UserQuota:
    """Get or create daily quota for user"""
    today = date.today()

    quota = db.query(UserQuota).filter(
        UserQuota.user_id == user.id,
        UserQuota.quota_date == today
    ).first()

    if not quota:
        # Create new quota for today
        max_clips = 999 if user.role.value == "admin" else 5  # Admin gets unlimited
        quota = UserQuota(
            user_id=user.id,
            quota_date=today,
            clips_created=0,
            max_clips=max_clips,
            is_premium=0  # TODO: Check user premium status
        )
        db.add(quota)
        db.commit()
        db.refresh(quota)

    return quota


async def process_clip_creation(clip_id: int, db: Session):
    """
    Background task to process clip creation
    In production, this should:
    1. Call Smart Clipper AI to determine optimal timing
    2. Use FFMPEG to extract video segment
    3. Generate subtitles for clip
    4. Upload to S3/MinIO
    5. Update clip status

    For now, this is a placeholder that simulates processing
    """
    # TODO: Implement actual clip processing pipeline
    # - Smart Clipper AI integration
    # - FFMPEG video extraction
    # - Subtitle generation
    # - S3/MinIO upload
    pass


# ============================================
# Clip Endpoints
# ============================================

@router.post("/create", response_model=ClipResponse, status_code=status.HTTP_201_CREATED)
async def create_clip(
    request: CreateClipRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new clip from video

    **Workflow**:
    1. Check user's daily quota (5 clips/day for free users)
    2. Validate video exists
    3. If no manual timing provided, Smart Clipper AI will determine optimal segment
    4. Queue clip processing job (FFMPEG extraction + subtitle generation)
    5. Return clip ID and status

    **Parameters**:
    - **video_id**: ID of source video (required)
    - **search_phrase**: Phrase to find in transcript (required for Smart Clipper)
    - **title**: Custom title for clip (optional)
    - **start_time**: Manual start time override (optional)
    - **end_time**: Manual end time override (optional)

    **Returns**:
    - Clip metadata with status "pending" or "processing"
    """
    # Check quota
    quota = get_or_create_quota(db, current_user)

    if not quota.has_quota_remaining():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily clip limit reached ({quota.max_clips} clips/day). Upgrade to Premium for unlimited clips."
        )

    # Verify video exists
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Validate manual timing if provided
    if request.start_time is not None and request.end_time is not None:
        if request.start_time >= request.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_time must be less than end_time"
            )

        if video.duration and request.end_time > video.duration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"end_time exceeds video duration ({video.duration}s)"
            )

        start_time = request.start_time
        end_time = request.end_time
    else:
        # Placeholder: In production, call Smart Clipper AI here
        # For now, use default 10-second clip starting at 0
        start_time = 0.0
        end_time = 10.0

    # Calculate duration
    duration = int(end_time - start_time)

    # Create clip record
    clip = Clip(
        user_id=current_user.id,
        video_id=video.id,
        title=request.title or f"Clip from {video.title}",
        search_phrase=request.search_phrase,
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        status=ClipStatus.PENDING
    )

    db.add(clip)
    db.commit()
    db.refresh(clip)

    # Increment quota usage
    quota.increment_usage()
    db.commit()

    # Queue background processing
    # TODO: In production, use Celery or similar task queue
    # background_tasks.add_task(process_clip_creation, clip.id, db)

    # Build response
    response_data = clip.to_dict()
    response_data["videoTitle"] = video.title
    response_data["videoThumbnailUrl"] = video.thumbnail_url

    return ClipResponse(**response_data)


@router.get("", response_model=ClipListResponse)
async def list_clips(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    video_id: Optional[int] = Query(None, description="Filter by video"),
    status: Optional[str] = Query(None, description="Filter by status (pending, processing, ready, failed)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's clips with pagination and filters

    **Parameters**:
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **video_id**: Filter by video ID
    - **status**: Filter by status (pending, processing, ready, failed)

    **Returns**:
    - List of clips with pagination metadata
    """
    # Build query
    query = db.query(Clip).filter(Clip.user_id == current_user.id)

    # Apply filters
    if video_id is not None:
        query = query.filter(Clip.video_id == video_id)

    if status:
        try:
            clip_status = ClipStatus[status.upper()]
            query = query.filter(Clip.status == clip_status)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Must be one of: pending, processing, ready, failed"
            )

    # Get total count
    total = query.count()

    # Apply pagination and sorting (newest first)
    offset = (page - 1) * page_size
    clips = query.order_by(desc(Clip.created_at)).offset(offset).limit(page_size).all()

    # Get video info
    video_ids = [c.video_id for c in clips]
    videos = {}
    if video_ids:
        video_list = db.query(Video).filter(Video.id.in_(video_ids)).all()
        videos = {v.id: {"title": v.title, "thumbnail": v.thumbnail_url} for v in video_list}

    # Build response items
    items = []
    for clip in clips:
        clip_dict = clip.to_dict()
        video_info = videos.get(clip.video_id, {})
        clip_dict["videoTitle"] = video_info.get("title")
        clip_dict["videoThumbnailUrl"] = video_info.get("thumbnail")
        items.append(ClipResponse(**clip_dict))

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return ClipListResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=total_pages
    )


@router.get("/{id}/status", response_model=ClipStatusResponse)
async def get_clip_status(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get clip processing status

    Useful for polling clip progress during processing.
    Frontend can call this endpoint every few seconds to update UI.

    **Parameters**:
    - **id**: Clip ID

    **Returns**:
    - Current status and progress information
    """
    # Find clip
    clip = db.query(Clip).filter(
        Clip.id == id,
        Clip.user_id == current_user.id
    ).first()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip not found"
        )

    # Calculate progress percentage (placeholder)
    progress_map = {
        ClipStatus.PENDING: 0,
        ClipStatus.PROCESSING: 50,
        ClipStatus.READY: 100,
        ClipStatus.FAILED: 0
    }

    # Estimate time remaining (placeholder)
    estimated_time = None
    if clip.status == ClipStatus.PROCESSING:
        estimated_time = 30  # 30 seconds placeholder

    return ClipStatusResponse(
        id=clip.id,
        status=clip.status.value,
        progress=progress_map.get(clip.status, 0),
        errorMessage=clip.error_message,
        clipUrl=clip.clip_url,
        estimatedTimeRemaining=estimated_time
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a clip

    Note: This does not restore quota usage.
    In production, consider:
    - Soft delete vs hard delete
    - Cleanup of S3/MinIO files
    - Quota restoration policy

    **Parameters**:
    - **id**: Clip ID
    """
    # Find clip
    clip = db.query(Clip).filter(
        Clip.id == id,
        Clip.user_id == current_user.id
    ).first()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip not found"
        )

    # TODO: Delete associated files from S3/MinIO
    # if clip.clip_key:
    #     s3_client.delete_object(Bucket=bucket, Key=clip.clip_key)

    db.delete(clip)
    db.commit()

    return None


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's current daily clip quota

    **Returns**:
    - Quota information including usage and limits
    - Time until quota resets (midnight)
    """
    quota = get_or_create_quota(db, current_user)

    # Calculate next reset time (midnight tonight)
    from datetime import timedelta
    tomorrow = date.today() + timedelta(days=1)
    next_reset = datetime.combine(tomorrow, datetime.min.time())

    return QuotaResponse(
        userId=quota.user_id,
        quotaDate=quota.quota_date.isoformat(),
        clipsCreated=quota.clips_created,
        maxClips=quota.max_clips,
        remaining=max(0, quota.max_clips - quota.clips_created),
        isPremium=quota.is_premium,
        nextResetAt=next_reset.isoformat()
    )


@router.patch("/{id}/visibility", response_model=ClipResponse)
async def update_clip_visibility(
    id: int,
    is_public: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update clip visibility (public/private)

    **Parameters**:
    - **id**: Clip ID
    - **is_public**: Whether clip should be public

    **Returns**:
    - Updated clip information
    """
    # Find clip
    clip = db.query(Clip).filter(
        Clip.id == id,
        Clip.user_id == current_user.id
    ).first()

    if not clip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clip not found"
        )

    # Update visibility
    clip.is_public = 1 if is_public else 0
    db.commit()
    db.refresh(clip)

    # Get video info
    video = db.query(Video).filter(Video.id == clip.video_id).first()

    # Build response
    response_data = clip.to_dict()
    if video:
        response_data["videoTitle"] = video.title
        response_data["videoThumbnailUrl"] = video.thumbnail_url

    return ClipResponse(**response_data)
