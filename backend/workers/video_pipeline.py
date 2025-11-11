"""
Video processing pipeline orchestrator
Chains all AI tasks: extract_audio -> transcribe -> chunk -> translate -> index
Updates video status at each step
"""
from celery import chain, group
from celery.exceptions import Retry
import os
import subprocess
from datetime import datetime
import logging

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.video import Video, VideoStatus, Subtitle, SubtitleSource
from models.transcript import Transcript, TranscriptSentence

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="workers.video_pipeline.process_video_pipeline", max_retries=3)
def process_video_pipeline(self, video_id: int):
    """
    Main orchestrator: chains the entire video processing pipeline

    Pipeline flow:
    1. Extract audio from video
    2. Transcribe audio with WhisperX
    3. Semantic chunk transcript
    4. Translate to 8 languages
    5. Index transcript in Elasticsearch

    Args:
        video_id: ID of the video to process

    Returns:
        dict: Pipeline completion status
    """
    logger.info(f"Starting video pipeline for video_id={video_id}")

    try:
        # Update video status to PROCESSING
        with get_db_context() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            video.status = VideoStatus.PROCESSING
            db.commit()
            logger.info(f"Video {video_id} status set to PROCESSING")

        # Chain the pipeline tasks
        # Each task will be executed sequentially, passing results forward
        pipeline = chain(
            extract_audio.si(video_id),
            transcribe_audio.s(video_id),
            semantic_chunk.s(video_id),
            translate_subtitles.s(video_id),
            index_transcript.s(video_id)
        )

        # Execute the pipeline
        result = pipeline.apply_async()

        logger.info(f"Video pipeline started for video_id={video_id}, task_id={result.id}")
        return {
            "status": "pipeline_started",
            "video_id": video_id,
            "task_id": result.id
        }

    except Exception as e:
        logger.error(f"Failed to start video pipeline for video_id={video_id}: {str(e)}")

        # Update video status to DRAFT on failure
        try:
            with get_db_context() as db:
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.status = VideoStatus.DRAFT
                    db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update video status on error: {str(db_error)}")

        # Retry the task
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.video_pipeline.extract_audio", max_retries=3)
def extract_audio(self, video_id: int):
    """
    Step 1: Extract audio from video file using FFMPEG

    Args:
        video_id: ID of the video

    Returns:
        str: Path to extracted audio file
    """
    logger.info(f"Extracting audio from video_id={video_id}")

    try:
        with get_db_context() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Download video from MinIO/S3
            video_path = f"/tmp/video_{video_id}.mp4"
            audio_path = f"/tmp/audio_{video_id}.wav"

            # TODO: Download video from MinIO using video.video_key
            # For now, assume video is already downloaded

            # Extract audio using FFMPEG
            command = [
                "ffmpeg",
                "-i", video_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",  # 16-bit PCM
                "-ar", "16000",  # 16kHz sample rate (WhisperX requirement)
                "-ac", "1",  # Mono
                "-y",  # Overwrite output
                audio_path
            ]

            subprocess.run(command, check=True, capture_output=True)
            logger.info(f"Audio extracted successfully: {audio_path}")

            return audio_path

    except subprocess.CalledProcessError as e:
        logger.error(f"FFMPEG failed for video_id={video_id}: {e.stderr}")
        raise self.retry(exc=e, countdown=60)

    except Exception as e:
        logger.error(f"Failed to extract audio from video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.video_pipeline.finalize_pipeline", max_retries=3)
def finalize_pipeline(self, video_id: int):
    """
    Final step: Mark video as PUBLISHED and clean up temporary files

    Args:
        video_id: ID of the video

    Returns:
        dict: Finalization status
    """
    logger.info(f"Finalizing pipeline for video_id={video_id}")

    try:
        with get_db_context() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Update video status to PUBLISHED
            video.status = VideoStatus.PUBLISHED
            video.published_at = datetime.utcnow()
            db.commit()

            logger.info(f"Video {video_id} published successfully")

            # Clean up temporary files
            audio_path = f"/tmp/audio_{video_id}.wav"
            video_path = f"/tmp/video_{video_id}.mp4"

            for path in [audio_path, video_path]:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Cleaned up: {path}")

            return {
                "status": "completed",
                "video_id": video_id,
                "published_at": video.published_at.isoformat()
            }

    except Exception as e:
        logger.error(f"Failed to finalize pipeline for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.video_pipeline.handle_pipeline_error", max_retries=0)
def handle_pipeline_error(self, video_id: int, error_message: str):
    """
    Error handler: Update video status on pipeline failure

    Args:
        video_id: ID of the video
        error_message: Error description

    Returns:
        dict: Error handling status
    """
    logger.error(f"Pipeline error for video_id={video_id}: {error_message}")

    try:
        with get_db_context() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = VideoStatus.DRAFT
                db.commit()
                logger.info(f"Video {video_id} status reverted to DRAFT due to error")

        return {
            "status": "error_handled",
            "video_id": video_id,
            "error": error_message
        }

    except Exception as e:
        logger.error(f"Failed to handle pipeline error for video_id={video_id}: {str(e)}")
        return {
            "status": "error_handling_failed",
            "video_id": video_id,
            "error": str(e)
        }
