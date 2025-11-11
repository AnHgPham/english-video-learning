"""
Clip creation and management tasks
Handles clip generation, quota management, and cleanup
"""
import os
import logging
from typing import Dict, List
from datetime import datetime, date, timedelta
from celery.exceptions import Retry
import requests

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.clip import Clip, ClipStatus, UserQuota
from models.video import Video
from models.transcript import TranscriptSentence
from models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="workers.clip_task.create_clip", max_retries=3)
def create_clip(self, user_id: int, video_id: int, search_phrase: str, start_time: float = None, end_time: float = None):
    """
    Create a video clip from search results
    Uses Smart Clipper AI to determine optimal clip boundaries if not provided

    Args:
        user_id: ID of the user creating the clip
        video_id: ID of the source video
        search_phrase: Search phrase that led to this clip
        start_time: Optional start time in seconds (if None, Smart Clipper determines it)
        end_time: Optional end time in seconds (if None, Smart Clipper determines it)

    Returns:
        dict: Clip creation status with clip_id
    """
    logger.info(f"Creating clip for user_id={user_id}, video_id={video_id}, phrase='{search_phrase}'")

    try:
        # Check user quota
        quota_check = check_user_quota(user_id)
        if not quota_check["has_quota"]:
            return {
                "status": "quota_exceeded",
                "user_id": user_id,
                "remaining": 0,
                "error": "Daily clip quota exceeded"
            }

        # If start/end times not provided, use Smart Clipper AI
        if start_time is None or end_time is None:
            clip_boundaries = determine_clip_boundaries(video_id, search_phrase)
            start_time = clip_boundaries["start_time"]
            end_time = clip_boundaries["end_time"]

        # Create clip record in database
        with get_db_context() as db:
            clip = Clip(
                user_id=user_id,
                video_id=video_id,
                title=search_phrase[:255],  # Use search phrase as title
                search_phrase=search_phrase,
                start_time=start_time,
                end_time=end_time,
                duration=int(end_time - start_time),
                status=ClipStatus.PENDING
            )
            db.add(clip)
            db.commit()
            clip_id = clip.id

            # Increment user quota
            increment_user_quota(user_id)

        logger.info(f"Clip record created: clip_id={clip_id}")

        # Trigger FFMPEG processing task asynchronously
        from workers.ffmpeg_task import process_clip_video
        process_clip_video.apply_async(args=[clip_id], countdown=1)

        return {
            "status": "created",
            "clip_id": clip_id,
            "user_id": user_id,
            "video_id": video_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration": int(end_time - start_time)
        }

    except Exception as e:
        logger.error(f"Failed to create clip for user_id={user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


def determine_clip_boundaries(video_id: int, search_phrase: str) -> Dict[str, float]:
    """
    Use Smart Clipper AI to determine optimal clip boundaries

    Args:
        video_id: ID of the video
        search_phrase: Search phrase to find in transcript

    Returns:
        dict: {"start_time": float, "end_time": float}
    """
    logger.info(f"Determining clip boundaries for video_id={video_id}, phrase='{search_phrase}'")

    try:
        # Get transcript sentences
        with get_db_context() as db:
            sentences = db.query(TranscriptSentence).filter(
                TranscriptSentence.video_id == video_id
            ).order_by(TranscriptSentence.sentence_index).all()

            if not sentences:
                raise ValueError(f"No sentences found for video_id={video_id}")

        # Find sentences matching search phrase
        matching_sentences = []
        for sentence in sentences:
            if search_phrase.lower() in sentence.text.lower():
                matching_sentences.append(sentence)

        if not matching_sentences:
            # Use first sentence as fallback
            matching_sentences = [sentences[0]]

        # Call Smart Clipper AI
        response = requests.post(
            f"{settings.SMART_CLIPPER_URL}/determine_boundaries",
            json={
                "sentences": [
                    {
                        "index": s.sentence_index,
                        "text": s.text,
                        "start": s.start_time,
                        "end": s.end_time
                    }
                    for s in sentences
                ],
                "search_phrase": search_phrase,
                "matching_indices": [s.sentence_index for s in matching_sentences]
            },
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        start_time = result.get("start_time", matching_sentences[0].start_time)
        end_time = result.get("end_time", matching_sentences[-1].end_time)

        # Ensure clip is at least 3 seconds and at most 60 seconds
        duration = end_time - start_time
        if duration < 3:
            end_time = start_time + 3
        elif duration > 60:
            end_time = start_time + 60

        logger.info(f"Clip boundaries determined: {start_time:.2f}s - {end_time:.2f}s")

        return {
            "start_time": start_time,
            "end_time": end_time
        }

    except requests.exceptions.RequestException as e:
        logger.warning(f"Smart Clipper API error: {str(e)}, using fallback")
        # Fallback: use first matching sentence ± 2 seconds
        if matching_sentences:
            start_time = max(0, matching_sentences[0].start_time - 2)
            end_time = matching_sentences[-1].end_time + 2
        else:
            start_time = 0
            end_time = 10

        return {
            "start_time": start_time,
            "end_time": end_time
        }


def check_user_quota(user_id: int) -> Dict:
    """
    Check if user has remaining clip quota for today

    Args:
        user_id: ID of the user

    Returns:
        dict: {"has_quota": bool, "remaining": int, "max_clips": int}
    """
    with get_db_context() as db:
        today = date.today()

        # Get or create quota record for today
        quota = db.query(UserQuota).filter(
            UserQuota.user_id == user_id,
            UserQuota.quota_date == today
        ).first()

        if not quota:
            # Create new quota record
            user = db.query(User).filter(User.id == user_id).first()
            is_premium = 0  # TODO: Check premium status

            quota = UserQuota(
                user_id=user_id,
                quota_date=today,
                clips_created=0,
                max_clips=settings.RATE_LIMIT_PREMIUM_CLIPS_PER_DAY if is_premium else settings.RATE_LIMIT_FREE_CLIPS_PER_DAY,
                is_premium=is_premium
            )
            db.add(quota)
            db.commit()

        has_quota = quota.has_quota_remaining()
        remaining = max(0, quota.max_clips - quota.clips_created)

        return {
            "has_quota": has_quota,
            "remaining": remaining,
            "max_clips": quota.max_clips,
            "used": quota.clips_created
        }


def increment_user_quota(user_id: int):
    """
    Increment user's clip usage for today

    Args:
        user_id: ID of the user
    """
    with get_db_context() as db:
        today = date.today()

        quota = db.query(UserQuota).filter(
            UserQuota.user_id == user_id,
            UserQuota.quota_date == today
        ).first()

        if quota:
            quota.increment_usage()
            db.commit()
            logger.info(f"User {user_id} quota updated: {quota.clips_created}/{quota.max_clips}")


@celery_app.task(bind=True, name="workers.clip_task.cleanup_old_clips", max_retries=2)
def cleanup_old_clips(self):
    """
    Periodic task: Clean up clips older than 30 days
    Scheduled to run daily at 2 AM (configured in celery_app.py)

    Returns:
        dict: Cleanup results
    """
    logger.info("Starting cleanup of old clips")

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        deleted_count = 0

        with get_db_context() as db:
            # Find old clips
            old_clips = db.query(Clip).filter(
                Clip.created_at < cutoff_date
            ).all()

            logger.info(f"Found {len(old_clips)} clips older than 30 days")

            for clip in old_clips:
                try:
                    # Delete clip files from storage
                    if clip.clip_key:
                        delete_from_storage(clip.clip_key)

                    if clip.subtitle_key:
                        delete_from_storage(clip.subtitle_key)

                    if clip.thumbnail_url:
                        # Extract key from URL and delete
                        # TODO: Implement thumbnail deletion
                        pass

                    # Delete database record
                    db.delete(clip)
                    deleted_count += 1

                except Exception as e:
                    logger.error(f"Failed to delete clip_id={clip.id}: {str(e)}")

            db.commit()

        logger.info(f"Cleaned up {deleted_count} old clips")

        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to cleanup old clips: {str(e)}")
        raise self.retry(exc=e, countdown=300)


@celery_app.task(bind=True, name="workers.clip_task.reset_daily_quotas", max_retries=2)
def reset_daily_quotas(self):
    """
    Periodic task: Reset daily clip quotas at midnight
    Scheduled to run daily at 00:00 (configured in celery_app.py)

    Returns:
        dict: Reset results
    """
    logger.info("Resetting daily clip quotas")

    try:
        today = date.today()
        yesterday = today - timedelta(days=1)

        with get_db_context() as db:
            # Archive yesterday's quota records (optional - for analytics)
            # For now, just ensure new quota records are created when needed

            # Count active users from yesterday
            yesterday_quotas = db.query(UserQuota).filter(
                UserQuota.quota_date == yesterday
            ).count()

            logger.info(f"Found {yesterday_quotas} quota records from yesterday")

        return {
            "status": "completed",
            "reset_date": today.isoformat(),
            "previous_quota_count": yesterday_quotas
        }

    except Exception as e:
        logger.error(f"Failed to reset daily quotas: {str(e)}")
        raise self.retry(exc=e, countdown=300)


def delete_from_storage(object_key: str):
    """
    Delete file from MinIO/S3 storage

    Args:
        object_key: Storage key/path to delete
    """
    # TODO: Implement actual MinIO/S3 deletion
    logger.info(f"Deleting from storage: {object_key}")

    try:
        # Placeholder for MinIO/S3 deletion
        # import boto3
        # s3_client = boto3.client('s3')
        # s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        pass

    except Exception as e:
        logger.error(f"Failed to delete {object_key}: {str(e)}")


@celery_app.task(bind=True, name="workers.clip_task.get_user_quota_status", max_retries=1)
def get_user_quota_status(self, user_id: int):
    """
    Get user's current quota status (for API endpoints)

    Args:
        user_id: ID of the user

    Returns:
        dict: Quota status
    """
    return check_user_quota(user_id)


@celery_app.task(bind=True, name="workers.clip_task.delete_clip", max_retries=2)
def delete_clip(self, clip_id: int):
    """
    Delete a specific clip and its files

    Args:
        clip_id: ID of the clip to delete

    Returns:
        dict: Deletion status
    """
    logger.info(f"Deleting clip_id={clip_id}")

    try:
        with get_db_context() as db:
            clip = db.query(Clip).filter(Clip.id == clip_id).first()

            if not clip:
                return {
                    "status": "error",
                    "error": f"Clip {clip_id} not found"
                }

            # Delete files from storage
            if clip.clip_key:
                delete_from_storage(clip.clip_key)

            if clip.subtitle_key:
                delete_from_storage(clip.subtitle_key)

            # Delete database record
            user_id = clip.user_id
            db.delete(clip)
            db.commit()

        logger.info(f"Clip {clip_id} deleted successfully")

        return {
            "status": "completed",
            "clip_id": clip_id,
            "user_id": user_id
        }

    except Exception as e:
        logger.error(f"Failed to delete clip_id={clip_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.clip_task.update_clip_status", max_retries=2)
def update_clip_status(self, clip_id: int, status: str, error_message: str = None):
    """
    Update clip processing status

    Args:
        clip_id: ID of the clip
        status: New status (pending/processing/ready/failed)
        error_message: Optional error message

    Returns:
        dict: Update status
    """
    logger.info(f"Updating clip_id={clip_id} status to {status}")

    try:
        with get_db_context() as db:
            clip = db.query(Clip).filter(Clip.id == clip_id).first()

            if not clip:
                raise ValueError(f"Clip {clip_id} not found")

            clip.status = ClipStatus(status)

            if error_message:
                clip.error_message = error_message

            if status == "ready":
                clip.completed_at = datetime.utcnow()

            db.commit()

        return {
            "status": "updated",
            "clip_id": clip_id,
            "new_status": status
        }

    except Exception as e:
        logger.error(f"Failed to update clip status: {str(e)}")
        raise self.retry(exc=e, countdown=30)
