"""
Elasticsearch indexing task
Indexes transcript sentences for semantic search
"""
import logging
from typing import Dict, List, Any
from celery.exceptions import Retry
from elasticsearch import Elasticsearch, helpers

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.transcript import TranscriptSentence
from models.video import Video

logger = logging.getLogger(__name__)

# Initialize Elasticsearch client
es_client = None
if settings.ELASTICSEARCH_URL:
    try:
        es_client = Elasticsearch([settings.ELASTICSEARCH_URL])
        logger.info(f"Elasticsearch client initialized: {settings.ELASTICSEARCH_URL}")
    except Exception as e:
        logger.error(f"Failed to initialize Elasticsearch client: {str(e)}")


@celery_app.task(bind=True, name="workers.indexing_task.index_transcript", max_retries=3)
def index_transcript(self, previous_result: Dict, video_id: int):
    """
    Index transcript sentences in Elasticsearch for semantic search

    Args:
        previous_result: Result from previous task (translate_subtitles)
        video_id: ID of the video being processed

    Returns:
        dict: Indexing results with document count
    """
    logger.info(f"Starting Elasticsearch indexing for video_id={video_id}")

    try:
        if not es_client:
            logger.warning("Elasticsearch client not initialized, skipping indexing")
            return {
                "status": "skipped",
                "video_id": video_id,
                "reason": "elasticsearch_not_configured"
            }

        # Ensure index exists
        ensure_transcript_index_exists()

        # Get transcript sentences from database
        with get_db_context() as db:
            sentences = db.query(TranscriptSentence).filter(
                TranscriptSentence.video_id == video_id
            ).order_by(TranscriptSentence.sentence_index).all()

            video = db.query(Video).filter(Video.id == video_id).first()

            if not sentences:
                raise ValueError(f"No sentences found for video_id={video_id}")

            if not video:
                raise ValueError(f"Video {video_id} not found")

        logger.info(f"Retrieved {len(sentences)} sentences for indexing")

        # Prepare documents for bulk indexing
        documents = []
        for sentence in sentences:
            doc = {
                "_index": settings.ELASTICSEARCH_INDEX_TRANSCRIPTS,
                "_id": f"{video_id}_{sentence.id}",
                "_source": {
                    "video_id": video_id,
                    "sentence_id": sentence.id,
                    "transcript_id": sentence.transcript_id,
                    "sentence_index": sentence.sentence_index,
                    "text": sentence.text,
                    "start_time": sentence.start_time,
                    "end_time": sentence.end_time,
                    "duration": sentence.end_time - sentence.start_time,
                    # Video metadata for filtering
                    "video_title": video.title,
                    "video_level": video.level.value,
                    "video_language": video.language,
                    "category_id": video.category_id,
                }
            }
            documents.append(doc)

        # Bulk index documents
        success_count, failed_items = helpers.bulk(
            es_client,
            documents,
            raise_on_error=False,
            raise_on_exception=False
        )

        logger.info(f"Indexed {success_count}/{len(documents)} documents for video_id={video_id}")

        if failed_items:
            logger.warning(f"Failed to index {len(failed_items)} documents")

        return {
            "status": "completed",
            "video_id": video_id,
            "indexed_count": success_count,
            "failed_count": len(failed_items),
            "total_sentences": len(sentences)
        }

    except Exception as e:
        logger.error(f"Failed to index transcript for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120)


def ensure_transcript_index_exists():
    """
    Create Elasticsearch index if it doesn't exist
    Sets up mappings for optimal search performance
    """
    index_name = settings.ELASTICSEARCH_INDEX_TRANSCRIPTS

    if es_client.indices.exists(index=index_name):
        logger.info(f"Index '{index_name}' already exists")
        return

    logger.info(f"Creating index '{index_name}'")

    # Index mapping with text analysis for semantic search
    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1,
            "analysis": {
                "analyzer": {
                    "english_analyzer": {
                        "type": "standard",
                        "stopwords": "_english_"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "video_id": {"type": "integer"},
                "sentence_id": {"type": "integer"},
                "transcript_id": {"type": "integer"},
                "sentence_index": {"type": "integer"},
                "text": {
                    "type": "text",
                    "analyzer": "english_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}  # For exact matching
                    }
                },
                "start_time": {"type": "float"},
                "end_time": {"type": "float"},
                "duration": {"type": "float"},
                "video_title": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "video_level": {"type": "keyword"},
                "video_language": {"type": "keyword"},
                "category_id": {"type": "integer"}
            }
        }
    }

    es_client.indices.create(index=index_name, body=mapping)
    logger.info(f"Index '{index_name}' created successfully")


@celery_app.task(bind=True, name="workers.indexing_task.delete_video_from_index", max_retries=2)
def delete_video_from_index(self, video_id: int):
    """
    Delete all documents for a video from Elasticsearch

    Args:
        video_id: ID of the video to delete

    Returns:
        dict: Deletion results
    """
    logger.info(f"Deleting video_id={video_id} from Elasticsearch")

    try:
        if not es_client:
            return {
                "status": "skipped",
                "video_id": video_id,
                "reason": "elasticsearch_not_configured"
            }

        # Delete by query
        query = {
            "query": {
                "term": {
                    "video_id": video_id
                }
            }
        }

        response = es_client.delete_by_query(
            index=settings.ELASTICSEARCH_INDEX_TRANSCRIPTS,
            body=query
        )

        deleted_count = response.get("deleted", 0)

        logger.info(f"Deleted {deleted_count} documents for video_id={video_id}")

        return {
            "status": "completed",
            "video_id": video_id,
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Failed to delete video_id={video_id} from index: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.indexing_task.reindex_video", max_retries=2)
def reindex_video(self, video_id: int):
    """
    Re-index a video (delete old + index new)

    Args:
        video_id: ID of the video to re-index

    Returns:
        dict: Re-indexing results
    """
    logger.info(f"Re-indexing video_id={video_id}")

    try:
        # Delete existing documents
        delete_result = delete_video_from_index(video_id)

        # Index new documents
        index_result = index_transcript({}, video_id)

        return {
            "status": "completed",
            "video_id": video_id,
            "deleted_count": delete_result.get("deleted_count", 0),
            "indexed_count": index_result.get("indexed_count", 0)
        }

    except Exception as e:
        logger.error(f"Failed to re-index video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.indexing_task.search_transcripts", max_retries=2)
def search_transcripts(self, query: str, video_id: int = None, limit: int = 10):
    """
    Search transcripts in Elasticsearch (for testing)

    Args:
        query: Search query text
        video_id: Optional video ID to filter by
        limit: Maximum number of results

    Returns:
        dict: Search results
    """
    logger.info(f"Searching transcripts: query='{query}', video_id={video_id}")

    try:
        if not es_client:
            return {
                "status": "error",
                "error": "elasticsearch_not_configured"
            }

        # Build search query
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "text": {
                                    "query": query,
                                    "fuzziness": "AUTO"
                                }
                            }
                        }
                    ]
                }
            },
            "size": limit,
            "sort": [
                {"_score": {"order": "desc"}},
                {"sentence_index": {"order": "asc"}}
            ]
        }

        # Add video filter if specified
        if video_id:
            search_body["query"]["bool"]["filter"] = [
                {"term": {"video_id": video_id}}
            ]

        # Execute search
        response = es_client.search(
            index=settings.ELASTICSEARCH_INDEX_TRANSCRIPTS,
            body=search_body
        )

        hits = response.get("hits", {}).get("hits", [])

        results = []
        for hit in hits:
            source = hit["_source"]
            results.append({
                "sentence_id": source["sentence_id"],
                "video_id": source["video_id"],
                "text": source["text"],
                "start_time": source["start_time"],
                "end_time": source["end_time"],
                "score": hit["_score"]
            })

        logger.info(f"Found {len(results)} results")

        return {
            "status": "completed",
            "query": query,
            "video_id": video_id,
            "total_hits": response.get("hits", {}).get("total", {}).get("value", 0),
            "results": results
        }

    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@celery_app.task(bind=True, name="workers.indexing_task.rebuild_entire_index", max_retries=1)
def rebuild_entire_index(self):
    """
    Rebuild the entire Elasticsearch index from scratch
    WARNING: This will delete all existing documents

    Returns:
        dict: Rebuild results
    """
    logger.warning("Rebuilding entire Elasticsearch index")

    try:
        if not es_client:
            return {
                "status": "error",
                "error": "elasticsearch_not_configured"
            }

        # Delete index if exists
        index_name = settings.ELASTICSEARCH_INDEX_TRANSCRIPTS
        if es_client.indices.exists(index=index_name):
            es_client.indices.delete(index=index_name)
            logger.info(f"Deleted index '{index_name}'")

        # Create index
        ensure_transcript_index_exists()

        # Get all videos with transcripts
        with get_db_context() as db:
            videos = db.query(Video).join(
                TranscriptSentence,
                Video.id == TranscriptSentence.video_id
            ).distinct().all()

            video_ids = [v.id for v in videos]

        logger.info(f"Found {len(video_ids)} videos to index")

        # Index each video
        success_count = 0
        failed_count = 0

        for video_id in video_ids:
            try:
                result = index_transcript({}, video_id)
                if result.get("status") == "completed":
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to index video_id={video_id}: {str(e)}")
                failed_count += 1

        return {
            "status": "completed",
            "total_videos": len(video_ids),
            "success_count": success_count,
            "failed_count": failed_count
        }

    except Exception as e:
        logger.error(f"Failed to rebuild index: {str(e)}")
        raise self.retry(exc=e, countdown=300)  # Wait 5 minutes before retry
