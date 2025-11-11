"""
Public Video API endpoints
Handles video listing, details, and view tracking
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from core.database import get_db
from models.video import Video, VideoStatus, VideoLevel, Category, Subtitle

router = APIRouter()


# ============================================
# Request/Response Models (Pydantic schemas)
# ============================================

class CategoryResponse(BaseModel):
    """Category response model"""
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    createdAt: str


class SubtitleResponse(BaseModel):
    """Subtitle response model"""
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


class VideoListItem(BaseModel):
    """Video item in list view (minimal fields)"""
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    duration: Optional[int] = None
    level: str
    language: str
    categoryId: Optional[int] = None
    viewCount: int
    status: str
    createdAt: str
    publishedAt: Optional[str] = None


class VideoDetail(BaseModel):
    """Detailed video response with all fields"""
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    videoUrl: str
    videoKey: str
    thumbnailUrl: Optional[str] = None
    duration: Optional[int] = None
    level: str
    language: str
    categoryId: Optional[int] = None
    uploadedBy: int
    status: str
    viewCount: int
    createdAt: str
    updatedAt: str
    publishedAt: Optional[str] = None
    category: Optional[CategoryResponse] = None
    subtitles: List[SubtitleResponse] = []


class VideoListResponse(BaseModel):
    """Paginated video list response"""
    total: int
    page: int
    page_size: int
    total_pages: int
    videos: List[VideoListItem]


class ViewCountResponse(BaseModel):
    """Response after incrementing view count"""
    video_id: int
    view_count: int
    message: str


# ============================================
# Public Video Endpoints
# ============================================

@router.get("", response_model=VideoListResponse)
async def list_videos(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    level: Optional[str] = Query(None, description="Filter by level (A1, A2, B1, B2, C1, C2)"),
    category: Optional[int] = Query(None, description="Filter by category ID"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: Session = Depends(get_db)
):
    """
    Get list of all published videos with optional filters

    Filters:
    - level: Filter by English proficiency level (A1-C2)
    - category: Filter by category ID
    - search: Search query for title and description

    Returns paginated results with total count
    """
    # Base query - only published videos
    query = db.query(Video).filter(Video.status == VideoStatus.PUBLISHED)

    # Apply filters
    if level:
        try:
            # Validate level enum
            level_enum = VideoLevel(level.upper())
            query = query.filter(Video.level == level_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid level. Must be one of: {', '.join([l.value for l in VideoLevel])}"
            )

    if category:
        query = query.filter(Video.category_id == category)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Video.title.like(search_term),
                Video.description.like(search_term)
            )
        )

    # Get total count before pagination
    total = query.count()

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size
    offset = (page - 1) * page_size

    # Apply pagination and ordering
    videos = query.order_by(Video.published_at.desc()).offset(offset).limit(page_size).all()

    # Convert to response model
    video_items = [
        VideoListItem(
            id=video.id,
            title=video.title,
            slug=video.slug,
            description=video.description,
            thumbnailUrl=video.thumbnail_url,
            duration=video.duration,
            level=video.level.value,
            language=video.language,
            categoryId=video.category_id,
            viewCount=video.view_count,
            status=video.status.value,
            createdAt=video.created_at.isoformat(),
            publishedAt=video.published_at.isoformat() if video.published_at else None
        )
        for video in videos
    ]

    return VideoListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        videos=video_items
    )


@router.get("/{video_id}", response_model=VideoDetail)
async def get_video_by_id(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed video information by ID

    Returns:
    - Full video details including category and subtitles
    - Only returns published videos
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.status == VideoStatus.PUBLISHED
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or not published"
        )

    # Build response with related data
    response = VideoDetail(
        id=video.id,
        title=video.title,
        slug=video.slug,
        description=video.description,
        videoUrl=video.video_url,
        videoKey=video.video_key,
        thumbnailUrl=video.thumbnail_url,
        duration=video.duration,
        level=video.level.value,
        language=video.language,
        categoryId=video.category_id,
        uploadedBy=video.uploaded_by,
        status=video.status.value,
        viewCount=video.view_count,
        createdAt=video.created_at.isoformat(),
        updatedAt=video.updated_at.isoformat(),
        publishedAt=video.published_at.isoformat() if video.published_at else None,
        category=None,
        subtitles=[]
    )

    # Add category if available
    if video.category:
        response.category = CategoryResponse(
            id=video.category.id,
            name=video.category.name,
            slug=video.category.slug,
            description=video.category.description,
            createdAt=video.category.created_at.isoformat()
        )

    # Add subtitles if available
    if video.subtitles:
        response.subtitles = [
            SubtitleResponse(
                id=sub.id,
                videoId=sub.video_id,
                language=sub.language,
                languageName=sub.language_name,
                subtitleUrl=sub.subtitle_url,
                subtitleKey=sub.subtitle_key,
                isDefault=sub.is_default,
                source=sub.source.value,
                createdAt=sub.created_at.isoformat(),
                updatedAt=sub.updated_at.isoformat()
            )
            for sub in video.subtitles
        ]

    return response


@router.get("/slug/{slug}", response_model=VideoDetail)
async def get_video_by_slug(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed video information by slug

    Returns:
    - Full video details including category and subtitles
    - Only returns published videos
    """
    video = db.query(Video).filter(
        Video.slug == slug,
        Video.status == VideoStatus.PUBLISHED
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or not published"
        )

    # Build response with related data
    response = VideoDetail(
        id=video.id,
        title=video.title,
        slug=video.slug,
        description=video.description,
        videoUrl=video.video_url,
        videoKey=video.video_key,
        thumbnailUrl=video.thumbnail_url,
        duration=video.duration,
        level=video.level.value,
        language=video.language,
        categoryId=video.category_id,
        uploadedBy=video.uploaded_by,
        status=video.status.value,
        viewCount=video.view_count,
        createdAt=video.created_at.isoformat(),
        updatedAt=video.updated_at.isoformat(),
        publishedAt=video.published_at.isoformat() if video.published_at else None,
        category=None,
        subtitles=[]
    )

    # Add category if available
    if video.category:
        response.category = CategoryResponse(
            id=video.category.id,
            name=video.category.name,
            slug=video.category.slug,
            description=video.category.description,
            createdAt=video.category.created_at.isoformat()
        )

    # Add subtitles if available
    if video.subtitles:
        response.subtitles = [
            SubtitleResponse(
                id=sub.id,
                videoId=sub.video_id,
                language=sub.language,
                languageName=sub.language_name,
                subtitleUrl=sub.subtitle_url,
                subtitleKey=sub.subtitle_key,
                isDefault=sub.is_default,
                source=sub.source.value,
                createdAt=sub.created_at.isoformat(),
                updatedAt=sub.updated_at.isoformat()
            )
            for sub in video.subtitles
        ]

    return response


@router.post("/{video_id}/view", response_model=ViewCountResponse)
async def increment_view_count(
    video_id: int,
    db: Session = Depends(get_db)
):
    """
    Increment the view count for a video

    This endpoint is called when a user starts watching a video.
    Only works for published videos.
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.status == VideoStatus.PUBLISHED
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found or not published"
        )

    # Increment view count
    video.view_count += 1
    db.commit()
    db.refresh(video)

    return ViewCountResponse(
        video_id=video.id,
        view_count=video.view_count,
        message="View count incremented successfully"
    )
