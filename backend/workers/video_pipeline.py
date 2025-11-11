"""
Video processing pipeline orchestrator
Chains all AI tasks: extract_audio -> transcribe -> chunk -> translate -> index
Updates video status at each step
"""
from celery import chain, group
from celery.exceptions import Retry
import os
import subprocess
import json
from datetime import datetime
import logging
from pathlib import Path

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.video import Video, VideoStatus, Subtitle, SubtitleSource
from models.transcript import Transcript, TranscriptSentence
from services.storage import storage_service

# Import pipeline tasks (will be used in chain)
# These imports happen after celery_app is initialized
import workers.stt_task as stt_module
import workers.chunking_task as chunking_module
import workers.translation_task as translation_module
import workers.indexing_task as indexing_module

logger = logging.getLogger(__name__)

# Constants
TEMP_DIR = "/tmp/video-processing"


def ensure_temp_dir():
    """Ensure temporary processing directory exists"""
    Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)


def cleanup_temp_files(*file_paths):
    """
    Delete temporary files

    Args:
        file_paths: Variable number of file paths to delete
    """
    for path in file_paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
                logger.info(f"Cleaned up: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {str(e)}")


def extract_video_metadata_sync(video_path: str) -> dict:
    """
    Extract video metadata using FFPROBE (synchronous)

    Args:
        video_path: Path to video file

    Returns:
        dict: Video metadata (duration, resolution, codec, etc.)
    """
    logger.info(f"Extracting metadata from: {video_path}")

    try:
        # Use ffprobe to get video metadata
        command = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        metadata = json.loads(result.stdout)

        # Extract useful information
        duration = float(metadata.get("format", {}).get("duration", 0))

        video_stream = next(
            (s for s in metadata.get("streams", []) if s.get("codec_type") == "video"),
            {}
        )

        return {
            "duration": duration,
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "codec": video_stream.get("codec_name"),
            "bitrate": metadata.get("format", {}).get("bit_rate"),
            "format": metadata.get("format", {}).get("format_name")
        }

    except Exception as e:
        logger.error(f"Failed to extract metadata: {str(e)}")
        return {
            "duration": 0,
            "width": None,
            "height": None,
            "codec": None,
            "bitrate": None,
            "format": None
        }


def generate_thumbnail_sync(video_path: str, output_path: str, timestamp: float = 1.0) -> str:
    """
    Generate thumbnail from video using FFMPEG (synchronous)

    Args:
        video_path: Path to video file
        output_path: Path to save thumbnail
        timestamp: Time in seconds to capture thumbnail (default: 1.0s)

    Returns:
        str: Path to thumbnail file
    """
    logger.info(f"Generating thumbnail at {timestamp}s")

    # FFMPEG command to extract frame
    command = [
        "ffmpeg",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",  # Extract 1 frame
        "-vf", "scale=640:-1",  # Scale to 640px width, maintain aspect ratio
        "-y",  # Overwrite output
        output_path
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(f"Thumbnail created: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"FFMPEG thumbnail error: {e.stderr}")
        raise


def download_video_from_minio(video_key: str, output_path: str) -> str:
    """
    Download video from MinIO to local file

    Args:
        video_key: Storage key of the video
        output_path: Path to save downloaded video

    Returns:
        str: Path to downloaded video file
    """
    logger.info(f"Downloading video from MinIO: {video_key}")

    try:
        # Get presigned URL and download using streaming
        presigned_url = storage_service.get_presigned_url(
            object_key=video_key,
            bucket_name=settings.MINIO_BUCKET_VIDEOS,
            expires_in=3600  # 1 hour
        )

        # Download file using requests or MinIO client
        if not settings.USE_AWS_S3:
            # Direct MinIO download
            storage_service.minio_client.fget_object(
                settings.MINIO_BUCKET_VIDEOS,
                video_key,
                output_path
            )
        else:
            # AWS S3 download
            storage_service.s3_client.download_file(
                settings.S3_BUCKET_NAME,
                video_key,
                output_path
            )

        logger.info(f"Video downloaded to: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to download video from MinIO: {str(e)}")
        raise


@celery_app.task(bind=True, name="workers.video_pipeline.process_video_pipeline", max_retries=3)
def process_video_pipeline(self, video_id: int):
    """
    Main orchestrator: chains the entire video processing pipeline

    Pipeline flow:
    1. Extract metadata and generate thumbnail (after upload)
    2. Extract audio from video
    3. Transcribe audio with WhisperX
    4. Semantic chunk transcript
    5. Translate to 8 languages
    6. Index transcript in Elasticsearch

    Args:
        video_id: ID of the video to process

    Returns:
        dict: Pipeline completion status
    """
    logger.info(f"Starting video pipeline for video_id={video_id}")

    try:
        # Ensure temp directory exists
        ensure_temp_dir()

        # Update video status to PROCESSING
        with get_db_context() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            if not video.video_key:
                raise ValueError(f"Video {video_id} has no video_key")

            video.status = VideoStatus.PROCESSING
            db.commit()
            logger.info(f"Video {video_id} status set to PROCESSING")

            # Download video temporarily to extract metadata and thumbnail
            video_temp_path = os.path.join(TEMP_DIR, f"video_{video_id}.mp4")

            try:
                # Download video from MinIO
                download_video_from_minio(video.video_key, video_temp_path)

                # Extract video metadata (duration, resolution)
                logger.info(f"Extracting metadata for video_id={video_id}")
                metadata = extract_video_metadata_sync(video_temp_path)

                # Generate thumbnail
                logger.info(f"Generating thumbnail for video_id={video_id}")
                thumbnail_temp_path = os.path.join(TEMP_DIR, f"thumbnail_{video_id}.jpg")
                generate_thumbnail_sync(video_temp_path, thumbnail_temp_path, timestamp=1.0)

                # Upload thumbnail to MinIO
                thumbnail_key = f"thumbnails/video_{video_id}.jpg"
                thumbnail_url = storage_service.upload_file_from_path(
                    file_path=thumbnail_temp_path,
                    object_key=thumbnail_key,
                    bucket_name=settings.MINIO_BUCKET_THUMBNAILS,
                    content_type="image/jpeg"
                )
                logger.info(f"Thumbnail uploaded: {thumbnail_url}")

                # Update video with metadata and thumbnail
                video.duration = int(metadata.get("duration", 0))
                video.resolution = f"{metadata.get('width', 0)}x{metadata.get('height', 0)}"
                video.thumbnail_url = thumbnail_url
                video.thumbnail_key = thumbnail_key
                db.commit()

                logger.info(f"Video metadata updated: duration={video.duration}s, resolution={video.resolution}")

                # Clean up temporary files
                cleanup_temp_files(thumbnail_temp_path, video_temp_path)

            except Exception as e:
                logger.error(f"Failed to extract metadata/thumbnail: {str(e)}")
                # Continue with pipeline even if metadata extraction fails
                cleanup_temp_files(video_temp_path, thumbnail_temp_path if 'thumbnail_temp_path' in locals() else None)

        # Chain the pipeline tasks
        # Each task will be executed sequentially, passing results forward
        # Week 5-6: extract_audio → transcribe_audio ✅
        # Week 7: semantic_chunk ✅
        # Week 8: translate_subtitles (8 languages in parallel) ✅
        # Week 9+: indexing (TODO)
        pipeline = chain(
            extract_audio.si(video_id),
            stt_module.transcribe_audio.s(video_id),
            chunking_module.semantic_chunk.s(video_id),
            translation_module.translate_subtitles.s(video_id),
            # TODO: Uncomment when implemented
            # indexing_module.index_transcript.s(video_id)
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

    Full implementation:
    - Download video from MinIO to /tmp/video-processing/
    - Use ffmpeg to extract audio
    - Upload audio file to MinIO audio/ bucket
    - Update video record with audio_key
    - Clean up temp files
    - Return audio file URL

    Args:
        video_id: ID of the video

    Returns:
        str: URL of extracted audio file
    """
    logger.info(f"Extracting audio from video_id={video_id}")

    video_path = None
    audio_path = None

    try:
        # Ensure temp directory exists
        ensure_temp_dir()

        with get_db_context() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            if not video.video_key:
                raise ValueError(f"Video {video_id} has no video_key")

            # Define file paths
            video_path = os.path.join(TEMP_DIR, f"video_{video_id}.mp4")
            audio_path = os.path.join(TEMP_DIR, f"audio_{video_id}.wav")

            # Download video from MinIO
            logger.info(f"Downloading video from MinIO: {video.video_key}")
            download_video_from_minio(video.video_key, video_path)

            # Extract audio using FFMPEG
            logger.info(f"Extracting audio with FFMPEG")
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

            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Audio extracted successfully: {audio_path}")

            # Upload audio to MinIO
            audio_key = f"audio/video_{video_id}.wav"
            logger.info(f"Uploading audio to MinIO: {audio_key}")

            audio_url = storage_service.upload_file_from_path(
                file_path=audio_path,
                object_key=audio_key,
                bucket_name=settings.MINIO_BUCKET_AUDIO,
                content_type="audio/wav"
            )

            logger.info(f"Audio uploaded: {audio_url}")

            # Update video record with audio_key
            video.audio_key = audio_key
            db.commit()

            logger.info(f"Video record updated with audio_key: {audio_key}")

            # Clean up temporary files
            cleanup_temp_files(video_path, audio_path)

            return audio_url

    except subprocess.CalledProcessError as e:
        logger.error(f"FFMPEG failed for video_id={video_id}: {e.stderr}")
        cleanup_temp_files(video_path, audio_path)
        raise self.retry(exc=e, countdown=60)

    except Exception as e:
        logger.error(f"Failed to extract audio from video_id={video_id}: {str(e)}")
        cleanup_temp_files(video_path, audio_path)
        raise self.retry(exc=e, countdown=60)


# Placeholder tasks for the pipeline (to be implemented in other modules)
@celery_app.task(bind=True, name="workers.video_pipeline.transcribe_audio", max_retries=3)
def transcribe_audio(self, audio_url: str, video_id: int):
    """
    Step 2: Transcribe audio using WhisperX

    Args:
        audio_url: URL of the audio file
        video_id: ID of the video

    Returns:
        str: Transcript ID or path
    """
    logger.info(f"Transcribing audio for video_id={video_id}")
    # TODO: Implement WhisperX transcription
    # This will be implemented in whisperx_task.py
    return f"transcript_{video_id}"


@celery_app.task(bind=True, name="workers.video_pipeline.semantic_chunk", max_retries=3)
def semantic_chunk(self, transcript_id: str, video_id: int):
    """
    Step 3: Semantic chunking of transcript

    Args:
        transcript_id: ID of the transcript
        video_id: ID of the video

    Returns:
        str: Chunked transcript ID
    """
    logger.info(f"Semantic chunking for video_id={video_id}")
    # TODO: Implement semantic chunking
    # This will be implemented in chunking_task.py
    return f"chunked_{video_id}"


@celery_app.task(bind=True, name="workers.video_pipeline.translate_subtitles", max_retries=3)
def translate_subtitles(self, chunked_id: str, video_id: int):
    """
    Step 4: Translate subtitles to 8 languages

    Args:
        chunked_id: ID of the chunked transcript
        video_id: ID of the video

    Returns:
        dict: Translation results
    """
    logger.info(f"Translating subtitles for video_id={video_id}")
    # TODO: Implement translation
    # This will be implemented in translation_task.py
    return {"status": "translated", "video_id": video_id}


@celery_app.task(bind=True, name="workers.video_pipeline.index_transcript", max_retries=3)
def index_transcript(self, translation_result: dict, video_id: int):
    """
    Step 5: Index transcript in Elasticsearch

    Args:
        translation_result: Results from translation step
        video_id: ID of the video

    Returns:
        dict: Indexing results
    """
    logger.info(f"Indexing transcript for video_id={video_id}")
    # TODO: Implement Elasticsearch indexing
    # This will be implemented in indexing_task.py

    # Update video status to PUBLISHED
    try:
        with get_db_context() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.status = VideoStatus.PUBLISHED
                video.published_at = datetime.utcnow()
                db.commit()
                logger.info(f"Video {video_id} published successfully")
    except Exception as e:
        logger.error(f"Failed to update video status: {str(e)}")

    return {"status": "indexed", "video_id": video_id}


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
            audio_path = os.path.join(TEMP_DIR, f"audio_{video_id}.wav")
            video_path = os.path.join(TEMP_DIR, f"video_{video_id}.mp4")
            thumbnail_path = os.path.join(TEMP_DIR, f"thumbnail_{video_id}.jpg")

            cleanup_temp_files(audio_path, video_path, thumbnail_path)

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
