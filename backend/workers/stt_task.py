"""
Speech-to-Text task using WhisperX API
Converts audio to word-level timestamped transcript and generates VTT subtitles
"""
import os
import requests
import logging
import tempfile
from typing import Dict, List, Any
from io import BytesIO
from celery.exceptions import Retry

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.video import Video, Subtitle, SubtitleSource
from models.transcript import Transcript
from services.storage import storage_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="workers.stt_task.transcribe_audio", max_retries=3)
def transcribe_audio(self, audio_url: str, video_id: int):
    """
    Transcribe audio file using WhisperX API

    Full pipeline:
    1. Download audio from MinIO to temp file
    2. Call WhisperX API
    3. Parse response and extract word-level timestamps
    4. Save to transcripts table with rawData JSON
    5. Generate VTT file with word-level timestamps
    6. Upload VTT to MinIO subtitles/ bucket
    7. Create subtitle record in database
    8. Clean up temp files
    9. Return transcript_id

    Args:
        audio_url: URL/path to the audio file in MinIO
        video_id: ID of the video being processed

    Returns:
        dict: Transcription result with transcript_id and subtitle info

    Raises:
        Retry: If API call fails (will retry up to 3 times)
    """
    logger.info(f"Starting transcription for video_id={video_id}, audio_url={audio_url}")

    temp_audio_path = None
    temp_vtt_path = None

    try:
        # Step 1: Download audio from MinIO to temp file
        logger.info(f"Downloading audio from MinIO: {audio_url}")
        temp_audio_path = download_audio_from_minio(audio_url, video_id)
        logger.info(f"Audio downloaded to: {temp_audio_path}")

        # Step 2: Call WhisperX API
        logger.info(f"Calling WhisperX API for video_id={video_id}")
        with open(temp_audio_path, 'rb') as audio_file:
            files = {'audio': audio_file}
            data = {
                'language': 'en',  # TODO: Get from video metadata
                'return_word_timestamps': True,
                'align': True  # Enable word alignment for accurate timestamps
            }

            response = requests.post(
                f"{settings.WHISPERX_API_URL}/transcribe",
                files=files,
                data=data,
                timeout=600  # 10 minutes timeout for large files
            )

            response.raise_for_status()
            result = response.json()

        logger.info(f"WhisperX API response received for video_id={video_id}")

        # Step 3: Parse WhisperX response
        transcript_data = parse_whisperx_response(result)
        segments = transcript_data.get("segments", [])

        # Step 4: Save to database (transcripts table)
        with get_db_context() as db:
            # Check if transcript already exists
            transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()

            if transcript:
                # Update existing transcript
                transcript.raw_data = transcript_data
                transcript.source = "whisperx"
                transcript.is_processed = 0  # Not yet chunked
                logger.info(f"Updated existing transcript for video_id={video_id}")
            else:
                # Create new transcript
                transcript = Transcript(
                    video_id=video_id,
                    language="en",  # TODO: Get from video metadata
                    source="whisperx",
                    raw_data=transcript_data,
                    is_processed=0
                )
                db.add(transcript)
                logger.info(f"Created new transcript for video_id={video_id}")

            db.commit()
            db.refresh(transcript)
            transcript_id = transcript.id

            logger.info(f"Transcript saved to database: transcript_id={transcript_id}")

        # Step 5: Generate VTT file with word-level timestamps
        logger.info(f"Generating VTT file for video_id={video_id}")
        vtt_content = generate_vtt_from_transcript(segments)

        # Step 6: Upload VTT to MinIO subtitles/ bucket
        logger.info(f"Uploading VTT file to MinIO for video_id={video_id}")
        with get_db_context() as db:
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            video_slug = video.slug

        # Create temp VTT file for upload
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False, encoding='utf-8') as vtt_file:
            vtt_file.write(vtt_content)
            temp_vtt_path = vtt_file.name

        # Upload to MinIO
        subtitle_key = f"{video_slug}_en.vtt"
        subtitle_url = storage_service.upload_file_from_path(
            file_path=temp_vtt_path,
            object_key=subtitle_key,
            bucket_name=settings.MINIO_BUCKET_SUBTITLES,
            content_type="text/vtt"
        )
        logger.info(f"VTT file uploaded to: {subtitle_url}")

        # Step 7: Create subtitle record in database
        with get_db_context() as db:
            # Check if subtitle already exists
            subtitle = db.query(Subtitle).filter(
                Subtitle.video_id == video_id,
                Subtitle.language == "en"
            ).first()

            if subtitle:
                # Update existing subtitle
                subtitle.subtitle_url = subtitle_url
                subtitle.subtitle_key = subtitle_key
                subtitle.source = SubtitleSource.AI_GENERATED
                subtitle.is_default = 1
                logger.info(f"Updated existing subtitle for video_id={video_id}")
            else:
                # Create new subtitle
                subtitle = Subtitle(
                    video_id=video_id,
                    language="en",
                    language_name="English",
                    subtitle_url=subtitle_url,
                    subtitle_key=subtitle_key,
                    is_default=1,
                    source=SubtitleSource.AI_GENERATED
                )
                db.add(subtitle)
                logger.info(f"Created new subtitle for video_id={video_id}")

            db.commit()
            db.refresh(subtitle)
            subtitle_id = subtitle.id

            logger.info(f"Subtitle saved to database: subtitle_id={subtitle_id}")

        # Step 8: Return result
        return {
            "status": "completed",
            "video_id": video_id,
            "transcript_id": transcript_id,
            "subtitle_id": subtitle_id,
            "word_count": len(transcript_data.get("words", [])),
            "subtitle_url": subtitle_url,
            "audio_url": audio_url
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"WhisperX API error for video_id={video_id}: {str(e)}")
        # Retry on API failures with exponential backoff
        raise self.retry(exc=e, countdown=120 * (2 ** self.request.retries))

    except Exception as e:
        logger.error(f"Failed to transcribe audio for video_id={video_id}: {str(e)}", exc_info=True)
        # Retry on other failures
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

    finally:
        # Step 9: Clean up temp files
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
                logger.info(f"Cleaned up temp audio file: {temp_audio_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp audio file: {e}")

        if temp_vtt_path and os.path.exists(temp_vtt_path):
            try:
                os.unlink(temp_vtt_path)
                logger.info(f"Cleaned up temp VTT file: {temp_vtt_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp VTT file: {e}")


def download_audio_from_minio(audio_url: str, video_id: int) -> str:
    """
    Download audio file from MinIO to a temporary file

    Args:
        audio_url: MinIO URL of the audio file
        video_id: Video ID (for logging)

    Returns:
        str: Path to the downloaded temporary file
    """
    try:
        # Parse the audio URL to extract bucket and key
        # Expected format: http://minio:9000/audio/{key}
        # or http://localhost:9000/audio/{key}
        if "/audio/" in audio_url:
            # Extract key from URL
            audio_key = audio_url.split("/audio/")[1]
            bucket_name = settings.MINIO_BUCKET_AUDIO
        else:
            raise ValueError(f"Invalid audio URL format: {audio_url}")

        logger.info(f"Downloading from bucket={bucket_name}, key={audio_key}")

        # Generate presigned URL for download
        download_url = storage_service.get_presigned_url(
            object_key=audio_key,
            bucket_name=bucket_name,
            expires_in=3600  # 1 hour
        )

        # Download file
        response = requests.get(download_url, timeout=300)  # 5 minutes timeout
        response.raise_for_status()

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.mp3', delete=False) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name

        logger.info(f"Audio downloaded successfully to: {temp_path}")
        return temp_path

    except Exception as e:
        logger.error(f"Failed to download audio for video_id={video_id}: {str(e)}")
        raise


def parse_whisperx_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse WhisperX API response into our internal format

    Args:
        response: Raw WhisperX API response

    Returns:
        dict: Parsed transcript with word-level timestamps
            Format: {
                "text": "Full transcript text",
                "words": [
                    {"word": "Hello", "start": 0.5, "end": 0.8, "score": 0.95},
                    ...
                ],
                "segments": [...]
            }
    """
    words = []
    full_text = []
    segments = response.get("segments", [])

    for segment in segments:
        segment_text = segment.get("text", "").strip()
        full_text.append(segment_text)

        # Extract word-level timestamps
        segment_words = segment.get("words", [])
        for word_info in segment_words:
            words.append({
                "word": word_info.get("word", ""),
                "start": word_info.get("start", 0.0),
                "end": word_info.get("end", 0.0),
                "score": word_info.get("score", 1.0)
            })

    return {
        "text": " ".join(full_text),
        "words": words,
        "segments": segments,
        "language": response.get("language", "en")
    }


def generate_vtt_from_transcript(segments: List[Dict[str, Any]]) -> str:
    """
    Convert WhisperX segments to WebVTT format

    Args:
        segments: List of WhisperX segments with word-level timestamps
            Each segment: {"text": "...", "start": 0.5, "end": 2.3, "words": [...]}

    Returns:
        str: VTT file content as string
    """
    vtt_lines = ["WEBVTT", ""]

    for i, segment in enumerate(segments, 1):
        # Get segment timing
        start_time = segment.get("start", 0.0)
        end_time = segment.get("end", 0.0)
        text = segment.get("text", "").strip()

        if not text:
            continue

        # Format timestamps
        start_vtt = format_vtt_timestamp(start_time)
        end_vtt = format_vtt_timestamp(end_time)

        # Add cue
        vtt_lines.append(f"{i}")
        vtt_lines.append(f"{start_vtt} --> {end_vtt}")
        vtt_lines.append(text)
        vtt_lines.append("")  # Empty line between cues

    return "\n".join(vtt_lines)


def format_vtt_timestamp(seconds: float) -> str:
    """
    Convert seconds to VTT timestamp format "HH:MM:SS.mmm"

    Args:
        seconds: Time in seconds (float)

    Returns:
        str: VTT formatted timestamp (e.g., "00:01:23.456")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


@celery_app.task(bind=True, name="workers.stt_task.validate_transcript", max_retries=2)
def validate_transcript(self, transcript_id: int):
    """
    Validate transcript quality and completeness

    Args:
        transcript_id: ID of the transcript to validate

    Returns:
        dict: Validation results
    """
    logger.info(f"Validating transcript_id={transcript_id}")

    try:
        with get_db_context() as db:
            transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()

            if not transcript:
                raise ValueError(f"Transcript {transcript_id} not found")

            raw_data = transcript.raw_data or {}
            words = raw_data.get("words", [])
            text = raw_data.get("text", "")

            # Validation checks
            validation_results = {
                "transcript_id": transcript_id,
                "is_valid": True,
                "checks": {
                    "has_text": len(text) > 0,
                    "has_words": len(words) > 0,
                    "has_timestamps": all(
                        isinstance(w.get("start"), (int, float)) and
                        isinstance(w.get("end"), (int, float))
                        for w in words
                    ),
                    "word_count": len(words),
                    "text_length": len(text)
                }
            }

            # Mark as invalid if any check fails
            validation_results["is_valid"] = all([
                validation_results["checks"]["has_text"],
                validation_results["checks"]["has_words"],
                validation_results["checks"]["has_timestamps"],
                validation_results["checks"]["word_count"] > 10  # At least 10 words
            ])

            logger.info(f"Transcript validation: {validation_results}")
            return validation_results

    except Exception as e:
        logger.error(f"Failed to validate transcript_id={transcript_id}: {str(e)}")
        raise self.retry(exc=e, countdown=30)


@celery_app.task(bind=True, name="workers.stt_task.retry_failed_transcription", max_retries=5)
def retry_failed_transcription(self, video_id: int, audio_url: str):
    """
    Retry transcription for failed videos with exponential backoff

    Args:
        video_id: ID of the video
        audio_url: URL to audio file

    Returns:
        dict: Retry status
    """
    logger.info(f"Retrying transcription for video_id={video_id}")

    try:
        # Use exponential backoff: 2^retry_count minutes
        countdown = 60 * (2 ** self.request.retries)

        return transcribe_audio(audio_url, video_id)

    except Exception as e:
        logger.error(f"Retry failed for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=countdown)
