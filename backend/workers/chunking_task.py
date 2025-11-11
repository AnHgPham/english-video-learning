"""
Semantic chunking task using semantic-chunker API
Breaks transcript into meaningful sentence segments
"""
import requests
import logging
import tempfile
from typing import Dict, List, Any
from celery.exceptions import Retry

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.transcript import Transcript, TranscriptSentence
from models.video import Video, Subtitle, SubtitleSource
from services.storage import storage_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="workers.chunking_task.semantic_chunk", max_retries=3)
def semantic_chunk(self, previous_result: Dict, video_id: int):
    """
    Chunk transcript into semantic sentences using semantic-chunker API

    Args:
        previous_result: Result from previous task (transcribe_audio)
        video_id: ID of the video being processed

    Returns:
        dict: Chunking results with sentence count

    Raises:
        Retry: If API call fails (will retry up to 3 times)
    """
    logger.info(f"Starting semantic chunking for video_id={video_id}")

    try:
        # Get transcript from database
        with get_db_context() as db:
            transcript = db.query(Transcript).filter(Transcript.video_id == video_id).first()

            if not transcript:
                raise ValueError(f"Transcript not found for video_id={video_id}")

            raw_data = transcript.raw_data or {}
            words = raw_data.get("words", [])

            if not words:
                raise ValueError(f"No words found in transcript for video_id={video_id}")

        logger.info(f"Retrieved transcript with {len(words)} words")

        # Call semantic-chunker API
        response = requests.post(
            f"{settings.SEMANTIC_CHUNKER_URL}/chunk",
            json={
                "words": words,
                "language": "en"  # TODO: Get from video metadata
            },
            timeout=300  # 5 minutes timeout
        )

        response.raise_for_status()
        result = response.json()

        logger.info(f"Semantic chunker API response received for video_id={video_id}")

        # Parse and save sentence chunks (API returns "chunks" not "sentences")
        chunks = result.get("chunks", [])
        sentence_count = save_sentence_chunks(transcript.id, video_id, chunks)

        # Mark transcript as processed
        with get_db_context() as db:
            transcript = db.query(Transcript).filter(Transcript.id == transcript.id).first()
            if transcript:
                transcript.is_processed = 1
                db.commit()

        logger.info(f"Saved {sentence_count} sentences for video_id={video_id}")

        # Regenerate VTT file from semantic sentences
        logger.info(f"Regenerating VTT file from semantic sentences for video_id={video_id}")
        regenerate_vtt_from_sentences(video_id, transcript.id)

        return {
            "status": "completed",
            "video_id": video_id,
            "transcript_id": transcript.id,
            "sentence_count": sentence_count
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Semantic chunker API error for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120)  # Wait 2 minutes before retry

    except Exception as e:
        logger.error(f"Failed to chunk transcript for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


def save_sentence_chunks(transcript_id: int, video_id: int, sentences: List[Dict[str, Any]]) -> int:
    """
    Save sentence chunks to database

    Args:
        transcript_id: ID of the transcript
        video_id: ID of the video
        sentences: List of sentence dictionaries from semantic-chunker API

    Returns:
        int: Number of sentences saved

    Sentence format:
        {
            "text": "Complete sentence text",
            "start": 0.5,
            "end": 3.2,
            "words": [{"word": "Hello", "start": 0.5, "end": 0.8}, ...]
        }
    """
    logger.info(f"Saving {len(sentences)} sentences for transcript_id={transcript_id}")

    with get_db_context() as db:
        # Delete existing sentences (in case of re-processing)
        db.query(TranscriptSentence).filter(
            TranscriptSentence.transcript_id == transcript_id
        ).delete()

        # Insert new sentences
        for index, sentence_data in enumerate(sentences):
            sentence = TranscriptSentence(
                transcript_id=transcript_id,
                video_id=video_id,
                sentence_index=index,
                text=sentence_data.get("text", ""),
                start_time=sentence_data.get("start", 0.0),
                end_time=sentence_data.get("end", 0.0),
                words=sentence_data.get("words", [])
            )
            db.add(sentence)

        db.commit()

    logger.info(f"Successfully saved {len(sentences)} sentences")
    return len(sentences)


@celery_app.task(bind=True, name="workers.chunking_task.rechunk_transcript", max_retries=2)
def rechunk_transcript(self, transcript_id: int):
    """
    Re-chunk an existing transcript (useful for fixing errors)

    Args:
        transcript_id: ID of the transcript to re-chunk

    Returns:
        dict: Re-chunking results
    """
    logger.info(f"Re-chunking transcript_id={transcript_id}")

    try:
        with get_db_context() as db:
            transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()

            if not transcript:
                raise ValueError(f"Transcript {transcript_id} not found")

            video_id = transcript.video_id

        # Call semantic_chunk with empty previous_result
        return semantic_chunk({}, video_id)

    except Exception as e:
        logger.error(f"Failed to re-chunk transcript_id={transcript_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.chunking_task.validate_chunks", max_retries=2)
def validate_chunks(self, transcript_id: int):
    """
    Validate sentence chunks for quality and completeness

    Args:
        transcript_id: ID of the transcript to validate

    Returns:
        dict: Validation results
    """
    logger.info(f"Validating chunks for transcript_id={transcript_id}")

    try:
        with get_db_context() as db:
            sentences = db.query(TranscriptSentence).filter(
                TranscriptSentence.transcript_id == transcript_id
            ).order_by(TranscriptSentence.sentence_index).all()

            if not sentences:
                return {
                    "transcript_id": transcript_id,
                    "is_valid": False,
                    "error": "No sentences found"
                }

            # Validation checks
            validation_results = {
                "transcript_id": transcript_id,
                "is_valid": True,
                "sentence_count": len(sentences),
                "checks": {
                    "has_sentences": len(sentences) > 0,
                    "sequential_indices": check_sequential_indices(sentences),
                    "no_timing_gaps": check_timing_continuity(sentences),
                    "all_have_text": all(s.text and len(s.text) > 0 for s in sentences),
                    "avg_sentence_length": sum(len(s.text) for s in sentences) / len(sentences) if sentences else 0
                }
            }

            # Overall validity
            validation_results["is_valid"] = all([
                validation_results["checks"]["has_sentences"],
                validation_results["checks"]["sequential_indices"],
                validation_results["checks"]["all_have_text"]
            ])

            logger.info(f"Chunk validation results: {validation_results}")
            return validation_results

    except Exception as e:
        logger.error(f"Failed to validate chunks for transcript_id={transcript_id}: {str(e)}")
        raise self.retry(exc=e, countdown=30)


def check_sequential_indices(sentences: List[TranscriptSentence]) -> bool:
    """Check if sentence indices are sequential (0, 1, 2, ...)"""
    expected_indices = list(range(len(sentences)))
    actual_indices = [s.sentence_index for s in sentences]
    return expected_indices == actual_indices


def check_timing_continuity(sentences: List[TranscriptSentence], max_gap: float = 5.0) -> bool:
    """
    Check if sentences have reasonable timing continuity
    Allow max 5 seconds gap between consecutive sentences
    """
    for i in range(len(sentences) - 1):
        current = sentences[i]
        next_sentence = sentences[i + 1]

        # Check for large gaps
        gap = next_sentence.start_time - current.end_time
        if gap > max_gap:
            logger.warning(f"Large gap detected: {gap}s between sentence {i} and {i+1}")
            return False

        # Check for overlaps (end before start)
        if current.end_time > next_sentence.start_time:
            logger.warning(f"Overlap detected between sentence {i} and {i+1}")
            return False

    return True


@celery_app.task(bind=True, name="workers.chunking_task.merge_short_sentences", max_retries=2)
def merge_short_sentences(self, transcript_id: int, min_length: int = 20):
    """
    Merge very short sentences with adjacent ones for better readability

    Args:
        transcript_id: ID of the transcript
        min_length: Minimum character length for a sentence

    Returns:
        dict: Merge results
    """
    logger.info(f"Merging short sentences for transcript_id={transcript_id}")

    try:
        with get_db_context() as db:
            sentences = db.query(TranscriptSentence).filter(
                TranscriptSentence.transcript_id == transcript_id
            ).order_by(TranscriptSentence.sentence_index).all()

            merged_count = 0
            i = 0

            while i < len(sentences) - 1:
                current = sentences[i]

                # If current sentence is too short, merge with next
                if len(current.text) < min_length:
                    next_sentence = sentences[i + 1]

                    # Merge text
                    current.text = f"{current.text} {next_sentence.text}"
                    current.end_time = next_sentence.end_time

                    # Merge words
                    if current.words and next_sentence.words:
                        current.words = current.words + next_sentence.words

                    # Delete next sentence
                    db.delete(next_sentence)
                    merged_count += 1

                    # Don't increment i, check merged sentence again
                else:
                    i += 1

            # Reindex remaining sentences
            remaining = db.query(TranscriptSentence).filter(
                TranscriptSentence.transcript_id == transcript_id
            ).order_by(TranscriptSentence.sentence_index).all()

            for idx, sentence in enumerate(remaining):
                sentence.sentence_index = idx

            db.commit()

            logger.info(f"Merged {merged_count} short sentences")

            return {
                "transcript_id": transcript_id,
                "merged_count": merged_count,
                "final_count": len(remaining)
            }

    except Exception as e:
        logger.error(f"Failed to merge short sentences for transcript_id={transcript_id}: {str(e)}")
        raise self.retry(exc=e, countdown=30)


def regenerate_vtt_from_sentences(video_id: int, transcript_id: int):
    """
    Regenerate VTT file from semantic sentences instead of raw WhisperX segments

    This creates better subtitles with complete sentences instead of arbitrary 3-5 second chunks.

    Args:
        video_id: ID of the video
        transcript_id: ID of the transcript

    Returns:
        str: URL of the regenerated VTT file
    """
    logger.info(f"Regenerating VTT from semantic sentences for video_id={video_id}")

    try:
        with get_db_context() as db:
            # Get video
            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Get sentences ordered by index
            sentences = db.query(TranscriptSentence).filter(
                TranscriptSentence.transcript_id == transcript_id
            ).order_by(TranscriptSentence.sentence_index).all()

            if not sentences:
                raise ValueError(f"No sentences found for transcript_id={transcript_id}")

            logger.info(f"Found {len(sentences)} sentences for VTT generation")

            # Generate VTT content
            vtt_lines = ["WEBVTT", ""]

            for sentence in sentences:
                # Format timestamps
                start_vtt = format_vtt_timestamp(sentence.start_time)
                end_vtt = format_vtt_timestamp(sentence.end_time)

                # Add cue with sentence index
                vtt_lines.append(f"{sentence.sentence_index + 1}")
                vtt_lines.append(f"{start_vtt} --> {end_vtt}")
                vtt_lines.append(sentence.text.strip())
                vtt_lines.append("")  # Empty line between cues

            vtt_content = "\n".join(vtt_lines)

            # Save to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False, encoding='utf-8') as vtt_file:
                vtt_file.write(vtt_content)
                temp_vtt_path = vtt_file.name

            # Upload to MinIO
            subtitle_key = f"{video.slug}_en_semantic.vtt"
            subtitle_url = storage_service.upload_file_from_path(
                file_path=temp_vtt_path,
                object_key=subtitle_key,
                bucket_name=settings.MINIO_BUCKET_SUBTITLES,
                content_type="text/vtt"
            )

            logger.info(f"VTT file uploaded to: {subtitle_url}")

            # Update subtitle record (replace the WhisperX-generated one)
            subtitle = db.query(Subtitle).filter(
                Subtitle.video_id == video_id,
                Subtitle.language == "en"
            ).first()

            if subtitle:
                # Update existing subtitle with semantic version
                subtitle.subtitle_url = subtitle_url
                subtitle.subtitle_key = subtitle_key
                subtitle.source = SubtitleSource.AI_GENERATED
                logger.info(f"Updated subtitle record with semantic VTT")
            else:
                # Create new subtitle (shouldn't happen, but handle it)
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
                logger.info(f"Created new subtitle record with semantic VTT")

            db.commit()

            # Clean up temp file
            try:
                import os
                os.unlink(temp_vtt_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp VTT file: {e}")

            logger.info(f"VTT regeneration complete for video_id={video_id}")
            return subtitle_url

    except Exception as e:
        logger.error(f"Failed to regenerate VTT for video_id={video_id}: {str(e)}")
        raise


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
