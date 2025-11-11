"""
FFMPEG video processing tasks
Handles video cutting, thumbnail generation, and format conversion
"""
import os
import subprocess
import logging
from typing import Dict, Tuple
from celery.exceptions import Retry
from datetime import datetime

from workers.celery_app import celery_app
from core.database import get_db_context
from core.config import settings
from models.clip import Clip, ClipStatus
from models.video import Video
from models.transcript import TranscriptSentence

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="workers.ffmpeg_task.process_clip_video", max_retries=3)
def process_clip_video(self, clip_id: int):
    """
    Process a video clip: cut video, generate thumbnail, create subtitle

    Args:
        clip_id: ID of the clip to process

    Returns:
        dict: Processing results with URLs
    """
    logger.info(f"Processing clip_id={clip_id}")

    try:
        # Update status to PROCESSING
        from workers.clip_task import update_clip_status
        update_clip_status(clip_id, "processing")

        # Get clip details
        with get_db_context() as db:
            clip = db.query(Clip).filter(Clip.id == clip_id).first()

            if not clip:
                raise ValueError(f"Clip {clip_id} not found")

            video = db.query(Video).filter(Video.id == clip.video_id).first()

            if not video:
                raise ValueError(f"Video {clip.video_id} not found")

        logger.info(f"Processing clip: {clip.start_time}s - {clip.end_time}s from video_id={video.id}")

        # Download source video from MinIO/S3
        source_video_path = download_video_from_storage(video.video_key)

        # Cut video clip
        clip_video_path = cut_video_clip(
            source_video_path,
            clip.start_time,
            clip.end_time,
            clip_id
        )

        # Generate thumbnail
        thumbnail_path = generate_thumbnail(clip_video_path, clip_id)

        # Generate subtitle for clip
        subtitle_path = generate_clip_subtitle(clip.video_id, clip.start_time, clip.end_time, clip_id)

        # Upload files to MinIO/S3
        clip_url = upload_to_storage(clip_video_path, f"clips/{clip_id}.mp4")
        thumbnail_url = upload_to_storage(thumbnail_path, f"thumbnails/clip_{clip_id}.jpg")
        subtitle_url = upload_to_storage(subtitle_path, f"clips/subtitles/{clip_id}.srt")

        # Update clip record
        with get_db_context() as db:
            clip = db.query(Clip).filter(Clip.id == clip_id).first()

            if clip:
                clip.clip_url = clip_url
                clip.clip_key = f"clips/{clip_id}.mp4"
                clip.thumbnail_url = thumbnail_url
                clip.subtitle_url = subtitle_url
                clip.subtitle_key = f"clips/subtitles/{clip_id}.srt"
                clip.status = ClipStatus.READY
                clip.completed_at = datetime.utcnow()
                db.commit()

        # Clean up temporary files
        cleanup_temp_files([source_video_path, clip_video_path, thumbnail_path, subtitle_path])

        logger.info(f"Clip {clip_id} processed successfully")

        return {
            "status": "completed",
            "clip_id": clip_id,
            "clip_url": clip_url,
            "thumbnail_url": thumbnail_url,
            "subtitle_url": subtitle_url
        }

    except Exception as e:
        logger.error(f"Failed to process clip_id={clip_id}: {str(e)}")

        # Update status to FAILED
        try:
            from workers.clip_task import update_clip_status
            update_clip_status(clip_id, "failed", str(e))
        except Exception as update_error:
            logger.error(f"Failed to update clip status: {str(update_error)}")

        raise self.retry(exc=e, countdown=60)


def download_video_from_storage(video_key: str) -> str:
    """
    Download video from MinIO/S3 to temporary file

    Args:
        video_key: Storage key of the video

    Returns:
        str: Path to downloaded video file
    """
    logger.info(f"Downloading video: {video_key}")

    # TODO: Implement actual MinIO/S3 download
    # For now, assume video is already available locally

    temp_path = f"/tmp/source_{video_key.replace('/', '_')}"

    # Placeholder: Copy from local storage
    # import boto3
    # s3_client = boto3.client('s3')
    # s3_client.download_file(settings.MINIO_BUCKET_VIDEOS, video_key, temp_path)

    logger.info(f"Video downloaded to: {temp_path}")
    return temp_path


def cut_video_clip(source_path: str, start_time: float, end_time: float, clip_id: int) -> str:
    """
    Cut video clip using FFMPEG

    Args:
        source_path: Path to source video
        start_time: Start time in seconds
        end_time: End time in seconds
        clip_id: ID of the clip (for output filename)

    Returns:
        str: Path to output clip file
    """
    logger.info(f"Cutting video: {start_time}s - {end_time}s")

    output_path = f"/tmp/clip_{clip_id}.mp4"
    duration = end_time - start_time

    # FFMPEG command to cut video
    # -ss: start time, -t: duration, -c copy: copy codec (fast, no re-encoding)
    command = [
        "ffmpeg",
        "-ss", str(start_time),
        "-i", source_path,
        "-t", str(duration),
        "-c", "copy",  # Copy codec (fast)
        "-avoid_negative_ts", "1",  # Fix timestamp issues
        "-y",  # Overwrite output
        output_path
    ]

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(f"Video clip created: {output_path}")
        return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"FFMPEG error: {e.stderr}")
        raise


def generate_thumbnail(video_path: str, clip_id: int, timestamp: float = 1.0) -> str:
    """
    Generate thumbnail from video using FFMPEG

    Args:
        video_path: Path to video file
        clip_id: ID of the clip
        timestamp: Time in seconds to capture thumbnail (default: 1.0s)

    Returns:
        str: Path to thumbnail file
    """
    logger.info(f"Generating thumbnail at {timestamp}s")

    output_path = f"/tmp/thumbnail_{clip_id}.jpg"

    # FFMPEG command to extract frame
    command = [
        "ffmpeg",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",  # Extract 1 frame
        "-vf", "scale=320:-1",  # Scale to 320px width, maintain aspect ratio
        "-y",  # Overwrite output
        output_path
    ]

    try:
        result = subprocess.run(
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


def generate_clip_subtitle(video_id: int, start_time: float, end_time: float, clip_id: int) -> str:
    """
    Generate SRT subtitle file for clip from transcript sentences

    Args:
        video_id: ID of the source video
        start_time: Clip start time
        end_time: Clip end time
        clip_id: ID of the clip

    Returns:
        str: Path to subtitle file
    """
    logger.info(f"Generating subtitle for clip {clip_id}")

    output_path = f"/tmp/clip_subtitle_{clip_id}.srt"

    try:
        # Get sentences within time range
        with get_db_context() as db:
            sentences = db.query(TranscriptSentence).filter(
                TranscriptSentence.video_id == video_id,
                TranscriptSentence.start_time >= start_time,
                TranscriptSentence.end_time <= end_time
            ).order_by(TranscriptSentence.sentence_index).all()

        if not sentences:
            logger.warning(f"No sentences found for clip time range")
            # Create empty subtitle file
            with open(output_path, 'w') as f:
                f.write("")
            return output_path

        # Generate SRT content
        srt_lines = []
        for index, sentence in enumerate(sentences, start=1):
            # Adjust timestamps relative to clip start
            adjusted_start = sentence.start_time - start_time
            adjusted_end = sentence.end_time - start_time

            # Ensure non-negative timestamps
            adjusted_start = max(0, adjusted_start)
            adjusted_end = max(0, adjusted_end)

            # Format timestamps
            start_ts = format_srt_timestamp(adjusted_start)
            end_ts = format_srt_timestamp(adjusted_end)

            # Add SRT entry
            srt_lines.append(f"{index}")
            srt_lines.append(f"{start_ts} --> {end_ts}")
            srt_lines.append(sentence.text)
            srt_lines.append("")  # Empty line

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_lines))

        logger.info(f"Subtitle created with {len(sentences)} sentences: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to generate subtitle: {str(e)}")
        # Return empty subtitle file on error
        with open(output_path, 'w') as f:
            f.write("")
        return output_path


def format_srt_timestamp(seconds: float) -> str:
    """
    Format seconds to SRT timestamp (HH:MM:SS,mmm)

    Args:
        seconds: Time in seconds

    Returns:
        str: Formatted timestamp
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def upload_to_storage(file_path: str, object_key: str) -> str:
    """
    Upload file to MinIO/S3 storage

    Args:
        file_path: Path to local file
        object_key: Storage key/path

    Returns:
        str: Public URL of uploaded file
    """
    logger.info(f"Uploading to storage: {object_key}")

    # TODO: Implement actual MinIO/S3 upload
    # For now, return mock URL

    # import boto3
    # s3_client = boto3.client('s3')
    # s3_client.upload_file(file_path, bucket_name, object_key)

    # Return mock URL
    bucket = settings.MINIO_BUCKET_CLIPS
    url = f"http://{settings.MINIO_ENDPOINT}/{bucket}/{object_key}"

    logger.info(f"File uploaded: {url}")
    return url


def cleanup_temp_files(file_paths: list):
    """
    Delete temporary files

    Args:
        file_paths: List of file paths to delete
    """
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Cleaned up: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete {path}: {str(e)}")


@celery_app.task(bind=True, name="workers.ffmpeg_task.extract_video_metadata", max_retries=2)
def extract_video_metadata(self, video_path: str):
    """
    Extract video metadata using FFPROBE

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

        import json
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
        raise self.retry(exc=e, countdown=30)


@celery_app.task(bind=True, name="workers.ffmpeg_task.convert_video_format", max_retries=2)
def convert_video_format(self, input_path: str, output_path: str, target_format: str = "mp4"):
    """
    Convert video to different format

    Args:
        input_path: Path to input video
        output_path: Path to output video
        target_format: Target format (mp4, webm, etc.)

    Returns:
        dict: Conversion results
    """
    logger.info(f"Converting video to {target_format}")

    try:
        command = [
            "ffmpeg",
            "-i", input_path,
            "-c:v", "libx264",  # H.264 codec
            "-c:a", "aac",  # AAC audio
            "-preset", "medium",  # Encoding speed vs quality
            "-crf", "23",  # Quality (lower = better, 23 is default)
            "-y",  # Overwrite output
            output_path
        ]

        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(f"Video converted: {output_path}")

        return {
            "status": "completed",
            "input_path": input_path,
            "output_path": output_path,
            "format": target_format
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"FFMPEG conversion error: {e.stderr}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.ffmpeg_task.compress_video", max_retries=2)
def compress_video(self, input_path: str, output_path: str, target_size_mb: int = 10):
    """
    Compress video to target file size

    Args:
        input_path: Path to input video
        output_path: Path to output video
        target_size_mb: Target file size in MB

    Returns:
        dict: Compression results
    """
    logger.info(f"Compressing video to ~{target_size_mb}MB")

    try:
        # Get video duration
        metadata = extract_video_metadata(input_path)
        duration = metadata.get("duration", 0)

        if duration == 0:
            raise ValueError("Could not determine video duration")

        # Calculate target bitrate (80% of target to leave room for audio)
        target_bitrate = int((target_size_mb * 8192) / duration * 0.8)  # kbps

        command = [
            "ffmpeg",
            "-i", input_path,
            "-c:v", "libx264",
            "-b:v", f"{target_bitrate}k",
            "-c:a", "aac",
            "-b:a", "128k",
            "-preset", "slow",  # Better compression
            "-y",
            output_path
        ]

        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        # Get output file size
        output_size = os.path.getsize(output_path) / (1024 * 1024)  # MB

        logger.info(f"Video compressed: {output_size:.2f}MB (target: {target_size_mb}MB)")

        return {
            "status": "completed",
            "input_path": input_path,
            "output_path": output_path,
            "target_size_mb": target_size_mb,
            "actual_size_mb": round(output_size, 2),
            "bitrate_kbps": target_bitrate
        }

    except Exception as e:
        logger.error(f"Video compression error: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, name="workers.ffmpeg_task.generate_video_preview", max_retries=2)
def generate_video_preview(self, video_path: str, output_path: str, duration: int = 10):
    """
    Generate short preview clip from video (first N seconds)

    Args:
        video_path: Path to source video
        output_path: Path to output preview
        duration: Preview duration in seconds

    Returns:
        dict: Preview generation results
    """
    logger.info(f"Generating {duration}s preview")

    try:
        command = [
            "ffmpeg",
            "-i", video_path,
            "-t", str(duration),
            "-c", "copy",
            "-y",
            output_path
        ]

        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(f"Preview generated: {output_path}")

        return {
            "status": "completed",
            "input_path": video_path,
            "output_path": output_path,
            "duration": duration
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Preview generation error: {e.stderr}")
        raise self.retry(exc=e, countdown=30)
