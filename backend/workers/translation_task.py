"""
Translation task using Google Gemini API
Translates English subtitles to 8 target languages and generates VTT files
"""
import os
import logging
import tempfile
from typing import Dict, List, Any
from celery import group
from celery.exceptions import Retry
from datetime import timedelta
import google.generativeai as genai

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.video import Video, Subtitle, SubtitleSource
from models.transcript import TranscriptSentence
from services.storage import storage_service

logger = logging.getLogger(__name__)

# Target languages for translation (8 languages)
TARGET_LANGUAGES = {
    "vi": "Vietnamese",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "th": "Thai"
}

# Configure Gemini API
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


@celery_app.task(bind=True, name="workers.translation_task.translate_subtitles", max_retries=3)
def translate_subtitles(self, previous_result: Dict, video_id: int):
    """
    Translate English subtitles to 8 languages using Gemini API
    Creates parallel translation tasks for all languages

    Args:
        previous_result: Result from previous task (semantic_chunk)
        video_id: ID of the video being processed

    Returns:
        dict: Translation status for all languages
    """
    logger.info(f"Starting subtitle translation for video_id={video_id}")

    try:
        # Create parallel translation tasks for all target languages
        translation_tasks = group([
            translate_to_language.s(video_id, lang_code, lang_name)
            for lang_code, lang_name in TARGET_LANGUAGES.items()
        ])

        # Execute all translations in parallel
        result = translation_tasks.apply_async()

        logger.info(f"Started translation tasks for {len(TARGET_LANGUAGES)} languages")

        return {
            "status": "translations_started",
            "video_id": video_id,
            "languages": list(TARGET_LANGUAGES.keys()),
            "task_group_id": result.id
        }

    except Exception as e:
        logger.error(f"Failed to start translations for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.translation_task.translate_to_language", max_retries=3)
def translate_to_language(self, video_id: int, language_code: str, language_name: str):
    """
    Translate subtitles to a specific language using Gemini API

    Args:
        video_id: ID of the video
        language_code: ISO 639-1 language code (vi, zh, ja, etc.)
        language_name: Full language name (Vietnamese, Chinese, etc.)

    Returns:
        dict: Translation results with subtitle file info
    """
    logger.info(f"Translating video_id={video_id} to {language_name} ({language_code})")

    try:
        # Get English sentences from database
        with get_db_context() as db:
            sentences = db.query(TranscriptSentence).filter(
                TranscriptSentence.video_id == video_id
            ).order_by(TranscriptSentence.sentence_index).all()

            if not sentences:
                raise ValueError(f"No sentences found for video_id={video_id}")

            video = db.query(Video).filter(Video.id == video_id).first()
            if not video:
                raise ValueError(f"Video {video_id} not found")

        logger.info(f"Retrieved {len(sentences)} sentences for translation")

        # Translate sentences using Gemini
        translated_sentences = translate_batch_with_gemini(
            sentences=[s.text for s in sentences],
            target_language=language_name,
            language_code=language_code
        )

        # Generate VTT file
        vtt_content = generate_vtt_file(sentences, translated_sentences)

        # Upload VTT to MinIO/S3
        subtitle_key = f"{video.slug}_{language_code}.vtt"
        subtitle_url = upload_subtitle_to_storage(vtt_content, subtitle_key)

        # Save subtitle record to database
        with get_db_context() as db:
            # Check if subtitle already exists
            subtitle = db.query(Subtitle).filter(
                Subtitle.video_id == video_id,
                Subtitle.language == language_code
            ).first()

            if subtitle:
                # Update existing subtitle
                subtitle.subtitle_url = subtitle_url
                subtitle.subtitle_key = subtitle_key
                subtitle.source = SubtitleSource.AI_GENERATED
            else:
                # Create new subtitle
                subtitle = Subtitle(
                    video_id=video_id,
                    language=language_code,
                    language_name=language_name,
                    subtitle_url=subtitle_url,
                    subtitle_key=subtitle_key,
                    is_default=1 if language_code == "vi" else 0,  # Vietnamese default
                    source=SubtitleSource.AI_GENERATED
                )
                db.add(subtitle)

            db.commit()
            subtitle_id = subtitle.id

        logger.info(f"Subtitle created: subtitle_id={subtitle_id}, language={language_code}")

        return {
            "status": "completed",
            "video_id": video_id,
            "language": language_code,
            "subtitle_id": subtitle_id,
            "subtitle_url": subtitle_url,
            "sentence_count": len(translated_sentences)
        }

    except Exception as e:
        logger.error(f"Failed to translate to {language_code} for video_id={video_id}: {str(e)}")
        raise self.retry(exc=e, countdown=120)


def translate_batch_with_gemini(sentences: List[str], target_language: str, language_code: str, batch_size: int = 50) -> List[str]:
    """
    Translate sentences in batches using Gemini API

    Args:
        sentences: List of English sentences to translate
        target_language: Target language name (Vietnamese, Chinese, etc.)
        language_code: ISO language code
        batch_size: Number of sentences per API call

    Returns:
        List[str]: Translated sentences
    """
    logger.info(f"Translating {len(sentences)} sentences to {target_language} in batches of {batch_size}")

    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set, returning original sentences")
        return sentences

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        translated_sentences = []

        # Process in batches
        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i + batch_size]

            # Create translation prompt
            prompt = f"""Translate the following English sentences to {target_language}.
Return ONLY the translated sentences, one per line, in the same order.
Do not add explanations, numbers, or any other text.

English sentences:
{chr(10).join(batch)}

{target_language} translations:"""

            # Call Gemini API
            response = model.generate_content(prompt)
            translations = response.text.strip().split('\n')

            # Clean up translations (remove empty lines, numbering, etc.)
            translations = [
                t.strip().lstrip('0123456789.-) ')
                for t in translations
                if t.strip()
            ]

            # Ensure we have the same number of translations
            if len(translations) != len(batch):
                logger.warning(f"Translation mismatch: expected {len(batch)}, got {len(translations)}")
                # Pad with original sentences if needed
                while len(translations) < len(batch):
                    translations.append(batch[len(translations)])

            translated_sentences.extend(translations[:len(batch)])

            logger.info(f"Translated batch {i//batch_size + 1}/{(len(sentences)-1)//batch_size + 1}")

        return translated_sentences

    except Exception as e:
        logger.error(f"Gemini translation error: {str(e)}")
        # Return original sentences on error
        return sentences


def generate_vtt_file(sentences: List[TranscriptSentence], translations: List[str]) -> str:
    """
    Generate VTT subtitle file from sentences and translations

    Args:
        sentences: List of TranscriptSentence objects with timing info
        translations: List of translated text (same order as sentences)

    Returns:
        str: VTT file content

    VTT Format:
        WEBVTT

        1
        00:00:00.500 --> 00:00:03.200
        First subtitle line

        2
        00:00:03.500 --> 00:00:07.800
        Second subtitle line
    """
    vtt_lines = ["WEBVTT", ""]

    for index, (sentence, translation) in enumerate(zip(sentences, translations), start=1):
        # Convert timestamps to VTT format (HH:MM:SS.mmm)
        start_time = format_vtt_timestamp(sentence.start_time)
        end_time = format_vtt_timestamp(sentence.end_time)

        # Add VTT cue
        vtt_lines.append(f"{index}")
        vtt_lines.append(f"{start_time} --> {end_time}")
        vtt_lines.append(translation)
        vtt_lines.append("")  # Empty line between cues

    return "\n".join(vtt_lines)


def format_vtt_timestamp(seconds: float) -> str:
    """
    Convert seconds to VTT timestamp format (HH:MM:SS.mmm)

    Args:
        seconds: Timestamp in seconds

    Returns:
        str: Formatted timestamp (e.g., "00:01:23.456")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def upload_subtitle_to_storage(content: str, object_key: str) -> str:
    """
    Upload subtitle file to MinIO/S3

    Args:
        content: VTT file content
        object_key: Storage key/path (e.g., "video-slug_vi.vtt")

    Returns:
        str: Public URL of the uploaded subtitle
    """
    logger.info(f"Uploading subtitle to storage: {object_key}")

    try:
        # Save content to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        # Upload to MinIO/S3
        subtitle_url = storage_service.upload_file_from_path(
            file_path=temp_path,
            object_key=object_key,
            bucket_name=settings.MINIO_BUCKET_SUBTITLES,
            content_type="text/vtt"
        )

        # Clean up temp file
        try:
            os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file: {e}")

        logger.info(f"Subtitle uploaded successfully: {subtitle_url}")
        return subtitle_url

    except Exception as e:
        logger.error(f"Failed to upload subtitle to storage: {str(e)}")
        raise


@celery_app.task(bind=True, name="workers.translation_task.retranslate_subtitle", max_retries=2)
def retranslate_subtitle(self, video_id: int, language_code: str):
    """
    Re-translate a specific subtitle (useful for fixing translation errors)

    Args:
        video_id: ID of the video
        language_code: Language to re-translate

    Returns:
        dict: Re-translation results
    """
    logger.info(f"Re-translating subtitle for video_id={video_id}, language={language_code}")

    try:
        language_name = TARGET_LANGUAGES.get(language_code)

        if not language_name:
            raise ValueError(f"Unsupported language code: {language_code}")

        return translate_to_language(video_id, language_code, language_name)

    except Exception as e:
        logger.error(f"Failed to re-translate subtitle: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.translation_task.validate_translation", max_retries=2)
def validate_translation(self, subtitle_id: int):
    """
    Validate translation quality (basic checks)

    Args:
        subtitle_id: ID of the subtitle to validate

    Returns:
        dict: Validation results
    """
    logger.info(f"Validating translation for subtitle_id={subtitle_id}")

    try:
        with get_db_context() as db:
            subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()

            if not subtitle:
                raise ValueError(f"Subtitle {subtitle_id} not found")

            # TODO: Download and parse SRT file from MinIO
            # For now, basic validation

            validation_results = {
                "subtitle_id": subtitle_id,
                "is_valid": True,
                "checks": {
                    "has_url": subtitle.subtitle_url is not None,
                    "has_key": subtitle.subtitle_key is not None,
                    "language": subtitle.language,
                    "source": subtitle.source.value
                }
            }

            validation_results["is_valid"] = all([
                validation_results["checks"]["has_url"],
                validation_results["checks"]["has_key"]
            ])

            return validation_results

    except Exception as e:
        logger.error(f"Failed to validate translation for subtitle_id={subtitle_id}: {str(e)}")
        raise self.retry(exc=e, countdown=30)
