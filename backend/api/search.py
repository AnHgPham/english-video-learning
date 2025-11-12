"""
Search API endpoints
Transcript Search with Elasticsearch Integration
Handles searching through video transcripts for phrases and context
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from elasticsearch import Elasticsearch

from core.database import get_db
from core.security import get_current_user
from core.config import settings
from models.user import User
from models.video import Video, VideoLevel
from models.transcript import TranscriptSentence

router = APIRouter()

# Initialize Elasticsearch client
es_client = None
if settings.ELASTICSEARCH_URL:
    try:
        es_client = Elasticsearch([settings.ELASTICSEARCH_URL])
    except Exception as e:
        print(f"Failed to initialize Elasticsearch client: {str(e)}")


# ============================================
# Request/Response Models (Pydantic schemas)
# ============================================

class SearchResultItem(BaseModel):
    """Individual search result"""
    id: int
    videoId: int
    videoTitle: str
    videoThumbnailUrl: Optional[str]
    text: str
    startTime: float
    endTime: float
    sentenceIndex: int

    # Highlight matched phrase
    highlightedText: Optional[str] = None
    matchScore: Optional[float] = None


class SearchResponse(BaseModel):
    """Search results with pagination"""
    results: List[SearchResultItem]
    total: int
    page: int
    pageSize: int
    totalPages: int
    query: str
    executionTimeMs: Optional[float] = None


class SearchSuggestion(BaseModel):
    """Auto-complete suggestion"""
    text: str
    frequency: int
    category: Optional[str] = None


# ============================================
# Search Endpoints
# ============================================

@router.get("", response_model=SearchResponse)
async def search_transcripts(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    video_id: Optional[int] = Query(None, description="Filter by video ID"),
    level: Optional[str] = Query(None, description="Filter by video level (A1, A2, B1, B2, C1, C2)"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search through video transcripts using Elasticsearch

    **Features**:
    - Full-text search with relevance scoring
    - Fuzzy matching for typo tolerance
    - Phrase matching with proximity
    - Highlighted matched terms in results
    - Sub-second search performance
    - Multi-field filtering (video, level, category)

    **Parameters**:
    - **q**: Search query (required)
    - **page**: Page number (default: 1)
    - **page_size**: Results per page (default: 20, max: 100)
    - **video_id**: Filter results by specific video
    - **level**: Filter by English level (A1-C2)
    - **category_id**: Filter by category

    **Returns**:
    - Matching transcript sentences with video context
    - Pagination metadata
    - Execution time
    """
    start_time = datetime.utcnow()

    # Use Elasticsearch if available, fallback to SQL
    if es_client:
        try:
            # Build Elasticsearch query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "text": {
                                        "query": q,
                                        "fuzziness": "AUTO",  # Typo tolerance
                                        "operator": "or"
                                    }
                                }
                            }
                        ],
                        "filter": []
                    }
                },
                "highlight": {
                    "fields": {
                        "text": {
                            "pre_tags": ["<mark>"],
                            "post_tags": ["</mark>"],
                            "fragment_size": 200,
                            "number_of_fragments": 1
                        }
                    }
                },
                "from": (page - 1) * page_size,
                "size": page_size,
                "sort": [
                    {"_score": {"order": "desc"}},  # Relevance first
                    {"sentence_index": {"order": "asc"}}
                ]
            }

            # Apply filters
            if video_id is not None:
                search_body["query"]["bool"]["filter"].append(
                    {"term": {"video_id": video_id}}
                )

            if level:
                try:
                    video_level = VideoLevel[level.upper()]
                    search_body["query"]["bool"]["filter"].append(
                        {"term": {"video_level": video_level.value}}
                    )
                except KeyError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid level: {level}. Must be one of: A1, A2, B1, B2, C1, C2"
                    )

            if category_id is not None:
                search_body["query"]["bool"]["filter"].append(
                    {"term": {"category_id": category_id}}
                )

            # Execute Elasticsearch query
            response = es_client.search(
                index=settings.ELASTICSEARCH_INDEX_TRANSCRIPTS,
                body=search_body
            )

            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            results = hits.get("hits", [])

            # Fetch video details from DB for the results
            video_ids = list(set(hit["_source"]["video_id"] for hit in results))
            videos_map = {}
            if video_ids:
                videos = db.query(Video).filter(Video.id.in_(video_ids)).all()
                videos_map = {v.id: v for v in videos}

            # Build response items
            items = []
            for hit in results:
                source = hit["_source"]
                video = videos_map.get(source["video_id"])

                if not video:
                    continue

                # Get highlighted text
                highlight = hit.get("highlight", {}).get("text", [])
                highlighted_text = highlight[0] if highlight else None

                items.append(SearchResultItem(
                    id=source["sentence_id"],
                    videoId=source["video_id"],
                    videoTitle=source["video_title"],
                    videoThumbnailUrl=video.thumbnail_url,
                    text=source["text"],
                    startTime=source["start_time"],
                    endTime=source["end_time"],
                    sentenceIndex=source["sentence_index"],
                    highlightedText=highlighted_text,
                    matchScore=round(hit["_score"], 2)
                ))

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Calculate total pages
            total_pages = (total + page_size - 1) // page_size

            return SearchResponse(
                results=items,
                total=total,
                page=page,
                pageSize=page_size,
                totalPages=total_pages,
                query=q,
                executionTimeMs=round(execution_time_ms, 2)
            )

        except Exception as e:
            # Log error and fallback to SQL
            print(f"Elasticsearch search failed: {str(e)}, falling back to SQL")

    # Fallback: SQL-based search
    query = db.query(TranscriptSentence, Video).join(
        Video, TranscriptSentence.video_id == Video.id
    )

    # Only search published videos
    query = query.filter(Video.status == "published")

    # Apply search filter
    search_term = f"%{q}%"
    query = query.filter(TranscriptSentence.text.ilike(search_term))

    # Apply filters
    if video_id is not None:
        query = query.filter(Video.id == video_id)

    if level:
        try:
            video_level = VideoLevel[level.upper()]
            query = query.filter(Video.level == video_level)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid level: {level}. Must be one of: A1, A2, B1, B2, C1, C2"
            )

    if category_id is not None:
        query = query.filter(Video.category_id == category_id)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    results = query.order_by(
        TranscriptSentence.video_id,
        TranscriptSentence.sentence_index
    ).offset(offset).limit(page_size).all()

    # Build response items
    items = []
    for sentence, video in results:
        # Simple highlighting
        highlighted_text = sentence.text.replace(
            q,
            f"<mark>{q}</mark>"
        ) if q.lower() in sentence.text.lower() else None

        items.append(SearchResultItem(
            id=sentence.id,
            videoId=video.id,
            videoTitle=video.title,
            videoThumbnailUrl=video.thumbnail_url,
            text=sentence.text,
            startTime=sentence.start_time,
            endTime=sentence.end_time,
            sentenceIndex=sentence.sentence_index,
            highlightedText=highlighted_text,
            matchScore=1.0
        ))

    # Calculate execution time
    end_time = datetime.utcnow()
    execution_time_ms = (end_time - start_time).total_seconds() * 1000

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return SearchResponse(
        results=items,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=total_pages,
        query=q,
        executionTimeMs=round(execution_time_ms, 2)
    )


@router.get("/suggestions", response_model=List[SearchSuggestion])
async def get_search_suggestions(
    q: str = Query(..., min_length=1, max_length=100, description="Partial search query"),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get auto-complete suggestions for search

    **NOTE**: Placeholder implementation
    In production, integrate with Elasticsearch completion suggester or
    use a dedicated autocomplete service.

    Current implementation:
    - Returns common phrases from transcripts starting with query
    - Limited to 10 suggestions

    **Parameters**:
    - **q**: Partial search query
    - **limit**: Maximum suggestions to return (default: 10, max: 20)

    **Returns**:
    - List of suggested phrases
    """
    # Placeholder: Return empty suggestions
    # TODO: Implement with Elasticsearch completion suggester
    # or build a phrase index for autocomplete

    # For now, we can return common words from transcripts
    search_term = f"{q}%"

    # This is a simplified version - in production use Elasticsearch
    results = db.query(TranscriptSentence.text).filter(
        TranscriptSentence.text.ilike(search_term)
    ).limit(limit).all()

    suggestions = []
    seen = set()

    for (text,) in results:
        # Extract phrases starting with query
        words = text.lower().split()
        for i, word in enumerate(words):
            if word.startswith(q.lower()):
                # Get phrase (word + next few words)
                phrase = " ".join(words[i:min(i+3, len(words))])
                if phrase not in seen and len(suggestions) < limit:
                    suggestions.append(SearchSuggestion(
                        text=phrase,
                        frequency=1,  # Placeholder
                        category="phrase"
                    ))
                    seen.add(phrase)

    return suggestions[:limit]


@router.get("/phrases", response_model=List[str])
async def get_popular_phrases(
    limit: int = Query(20, ge=1, le=50, description="Number of phrases"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get popular search phrases from transcript database

    **NOTE**: Placeholder implementation
    In production, this should be powered by:
    - Elasticsearch aggregations for popular terms
    - Search analytics tracking user queries
    - Phrase extraction from transcripts

    Current implementation:
    - Returns placeholder popular phrases

    **Parameters**:
    - **limit**: Maximum phrases to return (default: 20, max: 50)

    **Returns**:
    - List of popular phrases
    """
    # Placeholder: Return common English phrases
    # TODO: Implement with Elasticsearch term aggregations
    popular_phrases = [
        "how are you",
        "thank you",
        "nice to meet you",
        "what is your name",
        "where are you from",
        "can you help me",
        "I don't understand",
        "could you please",
        "excuse me",
        "have a good day",
        "see you later",
        "how much is it",
        "what time is it",
        "I would like to",
        "it's my pleasure",
        "you're welcome",
        "I'm sorry",
        "no problem",
        "let me know",
        "as soon as possible"
    ]

    return popular_phrases[:limit]


@router.get("/context/{sentence_id}", response_model=List[SearchResultItem])
async def get_sentence_context(
    sentence_id: int,
    before: int = Query(2, ge=0, le=10, description="Sentences before"),
    after: int = Query(2, ge=0, le=10, description="Sentences after"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get surrounding context for a specific sentence
    Useful for showing more context around search results

    **Parameters**:
    - **sentence_id**: ID of the target sentence
    - **before**: Number of sentences before (default: 2, max: 10)
    - **after**: Number of sentences after (default: 2, max: 10)

    **Returns**:
    - List of sentences including target and surrounding context
    """
    # Get target sentence
    target = db.query(TranscriptSentence, Video).join(
        Video, TranscriptSentence.video_id == Video.id
    ).filter(TranscriptSentence.id == sentence_id).first()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sentence not found"
        )

    target_sentence, target_video = target

    # Get context sentences
    start_index = max(0, target_sentence.sentence_index - before)
    end_index = target_sentence.sentence_index + after

    context_sentences = db.query(TranscriptSentence, Video).join(
        Video, TranscriptSentence.video_id == Video.id
    ).filter(
        TranscriptSentence.video_id == target_video.id,
        TranscriptSentence.sentence_index >= start_index,
        TranscriptSentence.sentence_index <= end_index
    ).order_by(TranscriptSentence.sentence_index).all()

    # Build response
    items = []
    for sentence, video in context_sentences:
        items.append(SearchResultItem(
            id=sentence.id,
            videoId=video.id,
            videoTitle=video.title,
            videoThumbnailUrl=video.thumbnail_url,
            text=sentence.text,
            startTime=sentence.start_time,
            endTime=sentence.end_time,
            sentenceIndex=sentence.sentence_index,
            highlightedText=None,
            matchScore=1.0 if sentence.id == sentence_id else 0.5
        ))

    return items
