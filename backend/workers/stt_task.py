"""
Speech-to-Text task using WhisperX API
Converts audio to word-level timestamped transcript
"""
import requests
import logging
from typing import Dict, List, Any
from celery.exceptions import Retry

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.video import Video
from models.transcript import Transcript

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="workers.stt_task.transcribe_audio", max_retries=3)
def transcribe_audio(self, audio_path: str, video_id: int):
    """
    Transcribe audio file using WhisperX API

    Args:
        audio_path: Path to the audio file (from extract_audio task)
        video_id: ID of the video being processed

    Returns:
        dict: Transcription result with word-level timestamps

    Raises:
        Retry: If API call fails (will retry up to 3 times)
    """
    logger.info(f"Transcribing audio for video_id={video_id}, audio_path={audio_path}")

    try:
        # Call WhisperX API
        with open(audio_path, 'rb') as audio_file:
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

        # Parse WhisperX response
        # Expected format: {"segments": [{"text": "...", "words": [...]}]}
        transcript_data = parse_whisperx_response(result)

        # Save to database
        with get_db_context() as db:
            # Check if transcript already exists
            transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()

            if transcript:
                # Update existing transcript
                transcript.raw_data = transcript_data
                transcript.source = "whisperx"
                transcript.is_processed = 0  # Not yet chunked
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

            db.commit()
            transcript_id = transcript.id

            logger.info(f"Transcript saved to database: transcript_id={transcript_id}")

        return {
            "status": "completed",
            "video_id": video_id,
            "transcript_id": transcript_id,
            "word_count": len(transcript_data.get("words", [])),
            "audio_path": audio_path
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"WhisperX API error for video_id={video_id}: {str(e)}")
        # Retry on API failures
        raise self.retry(exc=e, countdown=120)  # Wait 2 minutes before retry

    except Exception as e:
        logger.error(f"Failed to transcribe audio for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


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
def retry_failed_transcription(self, video_id: int, audio_path: str):
    """
    Retry transcription for failed videos with exponential backoff

    Args:
        video_id: ID of the video
        audio_path: Path to audio file

    Returns:
        dict: Retry status
    """
    logger.info(f"Retrying transcription for video_id={video_id}")

    try:
        # Use exponential backoff: 2^retry_count minutes
        countdown = 60 * (2 ** self.request.retries)

        return transcribe_audio(audio_path, video_id)

    except Exception as e:
        logger.error(f"Retry failed for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=countdown)
