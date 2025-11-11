"""
Admin API endpoints
Handles administrative operations for videos, dashboard, and system management
All endpoints require admin authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from core.database import get_db
from core.security import get_current_admin
from models.user import User, UserRole
from models.video import Video, VideoStatus, VideoLevel, Category, Subtitle
from models.transcript import Transcript, TranscriptSentence

router = APIRouter()


# ============================================
# Request/Response Models (Pydantic schemas)
# ============================================

class DashboardStats(BaseModel):
    """Dashboard statistics response"""
    total_videos: int
    total_users: int
    total_admin_users: int
    videos_by_status: dict
    videos_by_level: dict
    recent_videos: List[dict]


class VideoListResponse(BaseModel):
    """Video list response with pagination"""
    total: int
    page: int
    page_size: int
    videos: List[dict]


class CreateVideoRequest(BaseModel):
    """Request to create a new video"""
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    video_url: str = Field(..., alias="videoUrl")
    video_key: str = Field(..., alias="videoKey")
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")
    duration: Optional[int] = None
    level: VideoLevel
    language: str = "en"
    category_id: Optional[int] = Field(None, alias="categoryId")
    status: VideoStatus = VideoStatus.DRAFT

    class Config:
        populate_by_name = True


class UpdateVideoRequest(BaseModel):
    """Request to update a video"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    video_url: Optional[str] = Field(None, alias="videoUrl")
    video_key: Optional[str] = Field(None, alias="videoKey")
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")
    duration: Optional[int] = None
    level: Optional[VideoLevel] = None
    language: Optional[str] = None
    category_id: Optional[int] = Field(None, alias="categoryId")
    status: Optional[VideoStatus] = None

    class Config:
        populate_by_name = True


class ProcessVideoResponse(BaseModel):
    """Response for video processing trigger"""
    message: str
    video_id: int
    status: str
    task_id: Optional[str] = None


# ============================================
# Admin Endpoints
# ============================================

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics

    Returns comprehensive statistics including:
    - Total videos count
    - Total users count
    - Videos grouped by status
    - Videos grouped by level
    - Recent videos (last 10)

    Requires: Admin authentication
    """
    # Total counts
    total_videos = db.query(Video).count()
    total_users = db.query(User).count()
    total_admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()

    # Videos by status
    videos_by_status_raw = (
        db.query(Video.status, func.count(Video.id))
        .group_by(Video.status)
        .all()
    )
    videos_by_status = {status.value: count for status, count in videos_by_status_raw}

    # Videos by level
    videos_by_level_raw = (
        db.query(Video.level, func.count(Video.id))
        .group_by(Video.level)
        .all()
    )
    videos_by_level = {level.value: count for level, count in videos_by_level_raw}

    # Recent videos (last 10)
    recent_videos_query = (
        db.query(Video)
        .order_by(desc(Video.created_at))
        .limit(10)
        .all()
    )
    recent_videos = [video.to_dict() for video in recent_videos_query]

    return DashboardStats(
        total_videos=total_videos,
        total_users=total_users,
        total_admin_users=total_admin_users,
        videos_by_status=videos_by_status,
        videos_by_level=videos_by_level,
        recent_videos=recent_videos
    )


@router.get("/videos", response_model=VideoListResponse)
async def list_all_videos(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[VideoStatus] = Query(None, description="Filter by status"),
    level: Optional[VideoLevel] = Query(None, description="Filter by level"),
    search: Optional[str] = Query(None, description="Search by title or description"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all videos including drafts

    Supports:
    - Pagination (page, page_size)
    - Filtering by status
    - Filtering by level
    - Search by title/description

    Requires: Admin authentication
    """
    # Build query
    query = db.query(Video)

    # Apply filters
    if status:
        query = query.filter(Video.status == status)

    if level:
        query = query.filter(Video.level == level)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Video.title.like(search_pattern)) |
            (Video.description.like(search_pattern))
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    videos_query = (
        query
        .order_by(desc(Video.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    videos = [video.to_dict() for video in videos_query]

    return VideoListResponse(
        total=total,
        page=page,
        page_size=page_size,
        videos=videos
    )


@router.post("/videos", status_code=status.HTTP_201_CREATED)
async def create_video(
    request: CreateVideoRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new video

    Creates a new video with the provided metadata.
    Initial status is typically DRAFT until processed.

    Requires: Admin authentication
    """
    # Check if slug already exists
    existing_video = db.query(Video).filter(Video.slug == request.slug).first()
    if existing_video:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video with slug '{request.slug}' already exists"
        )

    # Check if category exists (if provided)
    if request.category_id:
        category = db.query(Category).filter(Category.id == request.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {request.category_id} not found"
            )

    # Create new video
    new_video = Video(
        title=request.title,
        slug=request.slug,
        description=request.description,
        video_url=request.video_url,
        video_key=request.video_key,
        thumbnail_url=request.thumbnail_url,
        duration=request.duration,
        level=request.level,
        language=request.language,
        category_id=request.category_id,
        uploaded_by=current_admin.id,
        status=request.status,
        view_count=0
    )

    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    return {
        "message": "Video created successfully",
        "video": new_video.to_dict()
    }


@router.put("/videos/{video_id}")
async def update_video(
    video_id: int,
    request: UpdateVideoRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update an existing video

    Updates video metadata. Only provided fields will be updated.
    If status is changed to PUBLISHED, published_at timestamp is set.

    Requires: Admin authentication
    """
    # Find video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found"
        )

    # Check slug uniqueness if being updated
    if request.slug and request.slug != video.slug:
        existing_video = db.query(Video).filter(Video.slug == request.slug).first()
        if existing_video:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video with slug '{request.slug}' already exists"
            )

    # Check category exists if being updated
    if request.category_id:
        category = db.query(Category).filter(Category.id == request.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {request.category_id} not found"
            )

    # Update fields (only if provided)
    update_data = request.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        # Convert camelCase to snake_case for database fields
        db_field = field
        if field == "videoUrl":
            db_field = "video_url"
        elif field == "videoKey":
            db_field = "video_key"
        elif field == "thumbnailUrl":
            db_field = "thumbnail_url"
        elif field == "categoryId":
            db_field = "category_id"

        setattr(video, db_field, value)

    # Set published_at if status changed to PUBLISHED
    if request.status == VideoStatus.PUBLISHED and video.published_at is None:
        video.published_at = datetime.utcnow()

    db.commit()
    db.refresh(video)

    return {
        "message": "Video updated successfully",
        "video": video.to_dict()
    }


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a video

    Permanently deletes a video and all associated data:
    - Subtitles
    - Transcripts
    - Transcript sentences

    Note: This does not delete the actual video file from storage.
    You may want to implement a cleanup job for orphaned files.

    Requires: Admin authentication
    """
    # Find video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found"
        )

    # Store video info for response
    video_title = video.title
    video_key = video.video_key

    # Delete video (cascade will handle related records)
    db.delete(video)
    db.commit()

    return {
        "message": "Video deleted successfully",
        "deleted_video": {
            "id": video_id,
            "title": video_title,
            "videoKey": video_key
        },
        "note": "Video file in storage needs to be deleted manually or via cleanup job"
    }


@router.post("/videos/{video_id}/process", response_model=ProcessVideoResponse)
async def trigger_video_processing(
    video_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Trigger AI processing pipeline for a video

    Initiates the complete AI processing pipeline:
    1. WhisperX transcription
    2. Semantic sentence chunking
    3. Vocabulary extraction
    4. Smart clip generation

    The video status will be updated to PROCESSING.
    This endpoint triggers an asynchronous Celery task.

    Requires: Admin authentication
    """
    # Find video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found"
        )

    # Check if video is already being processed
    if video.status == VideoStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video is already being processed"
        )

    # Update video status to PROCESSING
    video.status = VideoStatus.PROCESSING
    db.commit()

    # TODO: Trigger Celery task for AI processing pipeline
    # Example:
    # from tasks.video_processing import process_video_pipeline
    # task = process_video_pipeline.delay(video_id)
    # task_id = task.id

    task_id = None  # Placeholder until Celery is integrated

    return ProcessVideoResponse(
        message="Video processing initiated successfully",
        video_id=video_id,
        status="processing",
        task_id=task_id
    )


@router.get("/videos/{video_id}")
async def get_video_details(
    video_id: int,
    include_subtitles: bool = Query(False, description="Include subtitles"),
    include_transcripts: bool = Query(False, description="Include transcripts"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific video

    Returns video metadata and optionally:
    - Subtitles
    - Transcripts with sentences

    Requires: Admin authentication
    """
    # Find video
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} not found"
        )

    # Build response
    response = video.to_dict(include_subtitles=include_subtitles)

    # Include transcripts if requested
    if include_transcripts:
        transcripts = db.query(Transcript).filter(Transcript.video_id == video_id).all()
        response["transcripts"] = [
            transcript.to_dict(include_sentences=True)
            for transcript in transcripts
        ]

    return response
