"""
Admin API endpoints
Handles administrative operations for videos, dashboard, and system management
All endpoints require admin authentication
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import uuid
import re

from core.database import get_db
from core.security import get_current_admin
from core.config import settings
from models.user import User, UserRole
from models.video import Video, VideoStatus, VideoLevel, Category, Subtitle
from models.transcript import Transcript, TranscriptSentence
from services.storage import storage_service

router = APIRouter()


# ============================================
# Utility Functions
# ============================================

def generate_slug_from_title(title: str) -> str:
    """
    Generate URL-friendly slug from video title

    Example: "Learning English - Part 1" -> "learning-english-part-1"
    """
    # Convert to lowercase
    slug = title.lower()
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def validate_video_file_extension(filename: str) -> bool:
    """
    Validate video file extension

    Supported formats: mp4, mov, avi, mkv
    """
    allowed_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
    file_ext = filename.lower()
    for ext in allowed_extensions:
        if file_ext.endswith(ext):
            return True
    return False


def get_content_type_from_extension(filename: str) -> str:
    """
    Get MIME content type from file extension
    """
    filename_lower = filename.lower()
    if filename_lower.endswith('.mp4'):
        return 'video/mp4'
    elif filename_lower.endswith('.mov'):
        return 'video/quicktime'
    elif filename_lower.endswith('.avi'):
        return 'video/x-msvideo'
    elif filename_lower.endswith('.mkv'):
        return 'video/x-matroska'
    return 'video/mp4'  # default


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
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    video_url: str = Field(..., alias="videoUrl")
    video_key: str = Field(..., alias="videoKey")
    thumbnail_url: Optional[str] = Field(None, alias="thumbnailUrl")
    duration: Optional[int] = None
    level: VideoLevel
    language: str = "en"
    category_id: Optional[int] = Field(None, alias="categoryId")
    status: VideoStatus = VideoStatus.DRAFT

    @validator('slug', always=True)
    def validate_slug(cls, v, values):
        if v:
            # Clean provided slug
            return generate_slug_from_title(v)
        # Auto-generate from title
        if 'title' in values:
            return generate_slug_from_title(values['title'])
        return v

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


class PrepareUploadRequest(BaseModel):
    """Request to prepare video upload"""
    filename: str = Field(..., min_length=1, description="Original filename with extension")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    content_type: Optional[str] = Field(None, description="MIME type (auto-detected if not provided)")

    @validator('filename')
    def validate_filename(cls, v):
        if not validate_video_file_extension(v):
            raise ValueError(
                'Invalid file extension. Supported formats: mp4, mov, avi, mkv'
            )
        return v

    @validator('file_size')
    def validate_file_size(cls, v):
        max_size = 5 * 1024 * 1024 * 1024  # 5GB
        if v > max_size:
            raise ValueError(f'File size exceeds maximum allowed size of 5GB')
        return v


class PrepareUploadResponse(BaseModel):
    """Response with presigned upload URL"""
    upload_id: str = Field(..., description="Unique upload identifier")
    upload_url: str = Field(..., description="Presigned URL for upload")
    upload_method: str = Field(default="POST", description="HTTP method to use (POST or PUT)")
    upload_fields: dict = Field(default={}, description="Additional form fields for POST")
    upload_headers: dict = Field(default={}, description="Headers to include with request")
    video_key: str = Field(..., description="Storage key for the video")
    expires_in: int = Field(..., description="URL expiration time in seconds")
    max_file_size: int = Field(..., description="Maximum allowed file size")


class CompleteUploadRequest(BaseModel):
    """Request to complete video upload"""
    upload_id: str = Field(..., description="Upload identifier from prepare endpoint")
    video_key: str = Field(..., description="Storage key from prepare endpoint")
    title: str = Field(..., min_length=1, max_length=255, description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    level: VideoLevel = Field(..., description="Video difficulty level")
    language: str = Field(default="en", description="Video language code")
    category_id: Optional[int] = Field(None, description="Category ID")
    slug: Optional[str] = Field(None, description="URL slug (auto-generated if not provided)")

    @validator('slug', always=True)
    def validate_slug(cls, v, values):
        if v:
            # Clean provided slug
            return generate_slug_from_title(v)
        # Auto-generate from title
        if 'title' in values:
            return generate_slug_from_title(values['title'])
        return v


class CompleteUploadResponse(BaseModel):
    """Response after completing upload"""
    message: str
    video: dict
    upload_metadata: dict


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


# ============================================
# Video Upload Endpoints (Chunked/Presigned)
# ============================================

@router.post("/videos/upload/prepare", response_model=PrepareUploadResponse)
async def prepare_video_upload(
    request: PrepareUploadRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Prepare video upload with presigned URL

    This endpoint generates a presigned URL that allows the client
    to upload video files directly to MinIO/S3 without proxying
    through the backend server. This is ideal for large files.

    Workflow:
    1. Client calls this endpoint with filename and file_size
    2. Backend generates presigned URL and returns upload credentials
    3. Client uploads directly to storage using the presigned URL
    4. Client calls /upload/complete to finalize the video record

    Benefits:
    - No backend bandwidth usage for video uploads
    - Supports chunked/streaming uploads
    - Progress tracking on client side
    - Faster uploads (direct to storage)

    Requires: Admin authentication
    """
    # Generate unique upload ID
    upload_id = str(uuid.uuid4())

    # Generate unique video key (storage path)
    file_extension = request.filename.split('.')[-1]
    video_key = f"videos/{datetime.utcnow().strftime('%Y/%m/%d')}/{upload_id}.{file_extension}"

    # Determine content type
    content_type = request.content_type or get_content_type_from_extension(request.filename)

    # Set maximum file size (5GB default)
    max_file_size = 5 * 1024 * 1024 * 1024  # 5GB

    # Validate file size
    if request.file_size > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({request.file_size} bytes) exceeds maximum allowed size of {max_file_size} bytes (5GB)"
        )

    # Generate presigned POST URL
    try:
        presigned_data = storage_service.get_presigned_post_url(
            object_key=video_key,
            bucket_name=settings.MINIO_BUCKET_VIDEOS,
            expires_in=3600,  # 1 hour expiration
            max_file_size=max_file_size,
            content_type=content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )

    # Prepare response
    return PrepareUploadResponse(
        upload_id=upload_id,
        upload_url=presigned_data["url"],
        upload_method=presigned_data.get("method", "POST"),
        upload_fields=presigned_data.get("fields", {}),
        upload_headers=presigned_data.get("headers", {}),
        video_key=video_key,
        expires_in=presigned_data["expires_in"],
        max_file_size=max_file_size
    )


@router.post("/videos/upload/complete", response_model=CompleteUploadResponse)
async def complete_video_upload(
    request: CompleteUploadRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Complete video upload and create video record

    After the client has successfully uploaded the video file to storage
    using the presigned URL, this endpoint finalizes the process by:
    1. Verifying the file exists in storage
    2. Retrieving file metadata (size, content type, etc.)
    3. Creating the video database record
    4. Auto-generating slug from title if not provided

    Workflow:
    1. Client uploads video using presigned URL from /upload/prepare
    2. Client calls this endpoint with upload_id, video_key, and metadata
    3. Backend verifies upload and creates video record
    4. Returns complete video information

    Requires: Admin authentication
    """
    # Verify file exists in storage
    try:
        file_exists = storage_service.file_exists(
            object_key=request.video_key,
            bucket_name=settings.MINIO_BUCKET_VIDEOS
        )
        if not file_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video file not found in storage. Please ensure upload completed successfully."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify file upload: {str(e)}"
        )

    # Get file metadata
    try:
        file_metadata = storage_service.get_file_metadata(
            object_key=request.video_key,
            bucket_name=settings.MINIO_BUCKET_VIDEOS
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file metadata: {str(e)}"
        )

    # Generate slug if not provided
    slug = request.slug
    if not slug:
        slug = generate_slug_from_title(request.title)

    # Ensure slug uniqueness
    base_slug = slug
    counter = 1
    while db.query(Video).filter(Video.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Check if category exists (if provided)
    if request.category_id:
        category = db.query(Category).filter(Category.id == request.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id {request.category_id} not found"
            )

    # Construct video URL
    if settings.USE_AWS_S3:
        video_url = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{request.video_key}"
    else:
        video_url = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_VIDEOS}/{request.video_key}"

    # Create video record
    new_video = Video(
        title=request.title,
        slug=slug,
        description=request.description,
        video_url=video_url,
        video_key=request.video_key,
        thumbnail_url=None,  # Will be generated later
        duration=None,  # Will be extracted during processing
        level=request.level,
        language=request.language,
        category_id=request.category_id,
        uploaded_by=current_admin.id,
        status=VideoStatus.DRAFT,
        view_count=0
    )

    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    # Prepare upload metadata for response
    upload_metadata = {
        "upload_id": request.upload_id,
        "video_key": request.video_key,
        "file_size": file_metadata.get("size"),
        "file_size_mb": round(file_metadata.get("size", 0) / (1024 * 1024), 2),
        "content_type": file_metadata.get("content_type"),
        "etag": file_metadata.get("etag"),
        "uploaded_at": file_metadata.get("last_modified"),
        "uploaded_by": current_admin.email
    }

    return CompleteUploadResponse(
        message="Video upload completed successfully",
        video=new_video.to_dict(),
        upload_metadata=upload_metadata
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
    Slug is auto-generated from title if not provided.

    Requires: Admin authentication
    """
    # Generate slug if not provided (validator already cleaned it)
    slug = request.slug
    if not slug:
        slug = generate_slug_from_title(request.title)

    # Ensure slug uniqueness
    base_slug = slug
    counter = 1
    while db.query(Video).filter(Video.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

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
        slug=slug,
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
