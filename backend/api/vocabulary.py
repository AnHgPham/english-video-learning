"""
Vocabulary API endpoints
MODULE 5: Vocabulary Management
Handles user's saved vocabulary from videos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.vocabulary import UserVocabulary
from models.video import Video

router = APIRouter()


# ============================================
# Request/Response Models (Pydantic schemas)
# ============================================

class SaveVocabularyRequest(BaseModel):
    """Request to save a new word to vocabulary"""
    word: str = Field(..., min_length=1, max_length=200, description="The word to save")
    translation: Optional[str] = Field(None, description="Vietnamese translation")
    phonetic: Optional[str] = Field(None, max_length=100, description="IPA phonetic transcription")
    definition: Optional[str] = Field(None, description="English definition")
    example: Optional[str] = Field(None, description="Example sentence")

    # Context from video
    video_id: Optional[int] = Field(None, description="Video ID where word was found")
    timestamp: Optional[int] = Field(None, ge=0, description="Timestamp in video (seconds)")
    context: Optional[str] = Field(None, description="Sentence containing the word")


class UpdateVocabularyRequest(BaseModel):
    """Request to update vocabulary learning progress"""
    mastery_level: Optional[int] = Field(None, ge=0, le=5, description="Mastery level (0-5)")
    translation: Optional[str] = None
    phonetic: Optional[str] = None
    definition: Optional[str] = None
    example: Optional[str] = None


class VocabularyResponse(BaseModel):
    """Vocabulary item response"""
    id: int
    userId: int
    word: str
    translation: Optional[str]
    phonetic: Optional[str]
    definition: Optional[str]
    example: Optional[str]
    videoId: Optional[int]
    timestamp: Optional[int]
    context: Optional[str]
    masteryLevel: int
    reviewCount: int
    lastReviewedAt: Optional[str]
    createdAt: str

    # Include video title if available
    videoTitle: Optional[str] = None


class VocabularyListResponse(BaseModel):
    """List of vocabulary items with pagination"""
    items: List[VocabularyResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int


# ============================================
# Vocabulary Endpoints
# ============================================

@router.post("/save", response_model=VocabularyResponse, status_code=status.HTTP_201_CREATED)
async def save_vocabulary(
    request: SaveVocabularyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save a word to user's vocabulary

    - **word**: The word to save (required)
    - **translation**: Vietnamese translation
    - **phonetic**: IPA phonetic transcription
    - **definition**: English definition
    - **example**: Example sentence
    - **video_id**: Video ID where word was found
    - **timestamp**: Timestamp in video (seconds)
    - **context**: Sentence containing the word
    """
    # Check if word already exists for this user
    existing = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == current_user.id,
        UserVocabulary.word == request.word.lower().strip()
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Word '{request.word}' already exists in your vocabulary"
        )

    # Verify video exists if video_id provided
    if request.video_id:
        video = db.query(Video).filter(Video.id == request.video_id).first()
        if not video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video not found"
            )

    # Create new vocabulary entry
    vocabulary = UserVocabulary(
        user_id=current_user.id,
        word=request.word.lower().strip(),
        translation=request.translation,
        phonetic=request.phonetic,
        definition=request.definition,
        example=request.example,
        video_id=request.video_id,
        timestamp=request.timestamp,
        context=request.context,
        mastery_level=0,
        review_count=0
    )

    db.add(vocabulary)
    db.commit()
    db.refresh(vocabulary)

    # Get video title if available
    video_title = None
    if vocabulary.video_id:
        video = db.query(Video).filter(Video.id == vocabulary.video_id).first()
        if video:
            video_title = video.title

    # Build response
    response_data = vocabulary.to_dict()
    response_data["videoTitle"] = video_title

    return VocabularyResponse(**response_data)


@router.get("", response_model=VocabularyListResponse)
async def list_vocabulary(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search words"),
    video_id: Optional[int] = Query(None, description="Filter by video"),
    mastery_level: Optional[int] = Query(None, ge=0, le=5, description="Filter by mastery level"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's saved vocabulary with pagination and filters

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **search**: Search in word, translation, definition
    - **video_id**: Filter by video ID
    - **mastery_level**: Filter by mastery level (0-5)
    """
    # Build query
    query = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == current_user.id
    )

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (UserVocabulary.word.like(search_term)) |
            (UserVocabulary.translation.like(search_term)) |
            (UserVocabulary.definition.like(search_term))
        )

    if video_id is not None:
        query = query.filter(UserVocabulary.video_id == video_id)

    if mastery_level is not None:
        query = query.filter(UserVocabulary.mastery_level == mastery_level)

    # Get total count
    total = query.count()

    # Apply pagination and sorting (newest first)
    offset = (page - 1) * page_size
    vocabulary_items = query.order_by(
        desc(UserVocabulary.created_at)
    ).offset(offset).limit(page_size).all()

    # Get video titles
    video_ids = [v.video_id for v in vocabulary_items if v.video_id]
    videos = {}
    if video_ids:
        video_list = db.query(Video).filter(Video.id.in_(video_ids)).all()
        videos = {v.id: v.title for v in video_list}

    # Build response items
    items = []
    for vocab in vocabulary_items:
        vocab_dict = vocab.to_dict()
        vocab_dict["videoTitle"] = videos.get(vocab.video_id) if vocab.video_id else None
        items.append(VocabularyResponse(**vocab_dict))

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return VocabularyListResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=total_pages
    )


@router.patch("/{id}", response_model=VocabularyResponse)
async def update_vocabulary(
    id: int,
    request: UpdateVocabularyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update vocabulary item (for learning progress)

    - **mastery_level**: Update mastery level (0-5)
    - **translation**: Update translation
    - **phonetic**: Update phonetic
    - **definition**: Update definition
    - **example**: Update example
    """
    # Find vocabulary item
    vocabulary = db.query(UserVocabulary).filter(
        UserVocabulary.id == id,
        UserVocabulary.user_id == current_user.id
    ).first()

    if not vocabulary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary item not found"
        )

    # Update fields
    update_data = request.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(vocabulary, field, value)

    # Update review tracking if mastery level changed
    if request.mastery_level is not None:
        vocabulary.review_count += 1
        vocabulary.last_reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(vocabulary)

    # Get video title if available
    video_title = None
    if vocabulary.video_id:
        video = db.query(Video).filter(Video.id == vocabulary.video_id).first()
        if video:
            video_title = video.title

    # Build response
    response_data = vocabulary.to_dict()
    response_data["videoTitle"] = video_title

    return VocabularyResponse(**response_data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vocabulary(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a word from vocabulary

    - **id**: Vocabulary item ID
    """
    # Find vocabulary item
    vocabulary = db.query(UserVocabulary).filter(
        UserVocabulary.id == id,
        UserVocabulary.user_id == current_user.id
    ).first()

    if not vocabulary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary item not found"
        )

    db.delete(vocabulary)
    db.commit()

    return None


@router.get("/stats", response_model=dict)
async def get_vocabulary_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get vocabulary statistics for current user

    Returns:
    - Total words saved
    - Words by mastery level
    - Recent learning activity
    """
    # Total words
    total_words = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == current_user.id
    ).count()

    # Words by mastery level
    mastery_counts = {}
    for level in range(6):  # 0-5
        count = db.query(UserVocabulary).filter(
            UserVocabulary.user_id == current_user.id,
            UserVocabulary.mastery_level == level
        ).count()
        mastery_counts[f"level_{level}"] = count

    # Words added this week
    from datetime import timedelta
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    words_this_week = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == current_user.id,
        UserVocabulary.created_at >= one_week_ago
    ).count()

    # Words reviewed this week
    words_reviewed_this_week = db.query(UserVocabulary).filter(
        UserVocabulary.user_id == current_user.id,
        UserVocabulary.last_reviewed_at >= one_week_ago
    ).count()

    return {
        "totalWords": total_words,
        "masteryDistribution": mastery_counts,
        "wordsAddedThisWeek": words_this_week,
        "wordsReviewedThisWeek": words_reviewed_this_week
    }
