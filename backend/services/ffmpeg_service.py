"""
FFMPEG Service - Video processing utilities
Handles audio extraction, thumbnail generation, metadata extraction, and video validation
"""
import os
import json
import subprocess
import tempfile
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse

from services.storage import storage_service
from core.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Custom exception for FFMPEG-related errors"""
    pass


class FFprobeError(Exception):
    """Custom exception for FFprobe-related errors"""
    pass


class FFmpegService:
    """
    Comprehensive FFMPEG service for video processing operations
    Supports local files and automatic S3/MinIO downloads
    """

    def __init__(self):
        """Initialize FFMPEG service and verify installation"""
        self._verify_ffmpeg_installation()

    def _verify_ffmpeg_installation(self) -> None:
        """
        Verify that ffmpeg and ffprobe are installed and accessible

        Raises:
            FFmpegError: If ffmpeg or ffprobe not found
        """
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=5
            )
            subprocess.run(
                ['ffprobe', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=5
            )
            logger.info("✅ FFMPEG and FFprobe verified successfully")
        except subprocess.CalledProcessError as e:
            error_msg = "FFMPEG or FFprobe not properly installed"
            logger.error(f"❌ {error_msg}: {e}")
            raise FFmpegError(error_msg)
        except FileNotFoundError:
            error_msg = "FFMPEG or FFprobe not found in system PATH"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)
        except subprocess.TimeoutExpired:
            error_msg = "FFMPEG verification timed out"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)

    def _is_s3_url(self, path: str) -> bool:
        """
        Check if path is an S3/MinIO URL

        Args:
            path: File path or URL

        Returns:
            True if S3 URL, False otherwise
        """
        parsed = urlparse(path)
        return parsed.scheme in ('http', 'https', 's3') and any([
            's3.amazonaws.com' in parsed.netloc,
            'minio' in parsed.netloc.lower(),
            parsed.netloc == settings.MINIO_ENDPOINT
        ])

    def _download_from_s3(self, s3_url: str) -> str:
        """
        Download file from S3/MinIO to temporary location

        Args:
            s3_url: S3 or MinIO URL

        Returns:
            Path to downloaded temporary file

        Raises:
            FFmpegError: If download fails
        """
        try:
            logger.info(f"📥 Downloading from S3: {s3_url}")

            # Parse URL to extract bucket and key
            parsed = urlparse(s3_url)
            path_parts = parsed.path.lstrip('/').split('/', 1)

            if len(path_parts) < 2:
                raise FFmpegError(f"Invalid S3 URL format: {s3_url}")

            bucket_name = path_parts[0]
            object_key = path_parts[1]

            # Create temporary file
            suffix = Path(object_key).suffix
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_path = temp_file.name
            temp_file.close()

            # Download using presigned URL
            presigned_url = storage_service.get_presigned_url(
                object_key=object_key,
                bucket_name=bucket_name,
                expires_in=3600
            )

            # Download with curl (more reliable than requests for large files)
            subprocess.run(
                ['curl', '-L', '-o', temp_path, presigned_url],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )

            logger.info(f"✅ Downloaded to: {temp_path}")
            return temp_path

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to download from S3: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)
        except Exception as e:
            error_msg = f"S3 download error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)

    def _get_local_path(self, video_path: str) -> Tuple[str, bool]:
        """
        Get local file path, downloading from S3 if necessary

        Args:
            video_path: Local path or S3 URL

        Returns:
            Tuple of (local_path, is_temporary)

        Raises:
            FFmpegError: If file not accessible
        """
        if self._is_s3_url(video_path):
            temp_path = self._download_from_s3(video_path)
            return temp_path, True
        else:
            if not os.path.exists(video_path):
                raise FFmpegError(f"Video file not found: {video_path}")
            return video_path, False

    def _cleanup_temp_file(self, file_path: str, is_temporary: bool) -> None:
        """
        Clean up temporary file if needed

        Args:
            file_path: Path to file
            is_temporary: Whether file is temporary
        """
        if is_temporary and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                logger.debug(f"🗑️ Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup temp file {file_path}: {e}")

    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        sample_rate: int = 16000,
        channels: int = 1
    ) -> str:
        """
        Extract audio from video file to MP3 format

        Args:
            video_path: Path to video file or S3 URL
            output_path: Path for output MP3 file
            sample_rate: Audio sample rate in Hz (default: 16000 for speech recognition)
            channels: Number of audio channels (1=mono, 2=stereo, default: 1)

        Returns:
            Path to extracted audio file

        Raises:
            FFmpegError: If extraction fails
        """
        local_path = None
        is_temp = False

        try:
            logger.info(f"🎵 Extracting audio from: {video_path}")

            # Get local path (download if S3)
            local_path, is_temp = self._get_local_path(video_path)

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-i', local_path,
                '-vn',  # No video
                '-acodec', 'libmp3lame',  # MP3 codec
                '-ar', str(sample_rate),  # Sample rate
                '-ac', str(channels),  # Channels
                '-b:a', '128k',  # Bitrate
                '-y',  # Overwrite output file
                output_path
            ]

            # Execute ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,  # 10 minutes max
                check=True
            )

            # Verify output file exists
            if not os.path.exists(output_path):
                raise FFmpegError("Audio extraction completed but output file not found")

            file_size = os.path.getsize(output_path)
            logger.info(f"✅ Audio extracted successfully: {output_path} ({file_size} bytes)")

            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = f"FFMPEG audio extraction failed: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)
        except subprocess.TimeoutExpired:
            error_msg = "Audio extraction timed out (>10 minutes)"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)
        except Exception as e:
            error_msg = f"Audio extraction error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)
        finally:
            # Cleanup temporary file
            if local_path:
                self._cleanup_temp_file(local_path, is_temp)

    def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp: float = 5.0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: int = 2
    ) -> str:
        """
        Generate thumbnail image from video at specified timestamp

        Args:
            video_path: Path to video file or S3 URL
            output_path: Path for output JPG file
            timestamp: Time in seconds to extract frame (default: 5.0)
            width: Output width in pixels (optional, maintains aspect ratio)
            height: Output height in pixels (optional, maintains aspect ratio)
            quality: JPEG quality 2-31 (lower is better, default: 2)

        Returns:
            Path to generated thumbnail

        Raises:
            FFmpegError: If thumbnail generation fails
        """
        local_path = None
        is_temp = False

        try:
            logger.info(f"🖼️ Generating thumbnail from: {video_path} at {timestamp}s")

            # Get local path (download if S3)
            local_path, is_temp = self._get_local_path(video_path)

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),  # Seek to timestamp
                '-i', local_path,
                '-vframes', '1',  # Extract single frame
                '-q:v', str(quality),  # JPEG quality
            ]

            # Add scaling if specified
            if width or height:
                if width and height:
                    scale_filter = f"scale={width}:{height}"
                elif width:
                    scale_filter = f"scale={width}:-1"  # Auto height
                else:
                    scale_filter = f"scale=-1:{height}"  # Auto width
                cmd.extend(['-vf', scale_filter])

            cmd.extend(['-y', output_path])  # Overwrite output

            # Execute ffmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,  # 1 minute max
                check=True
            )

            # Verify output file exists
            if not os.path.exists(output_path):
                raise FFmpegError("Thumbnail generation completed but output file not found")

            file_size = os.path.getsize(output_path)
            logger.info(f"✅ Thumbnail generated successfully: {output_path} ({file_size} bytes)")

            return output_path

        except subprocess.CalledProcessError as e:
            error_msg = f"FFMPEG thumbnail generation failed: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)
        except subprocess.TimeoutExpired:
            error_msg = "Thumbnail generation timed out (>1 minute)"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)
        except Exception as e:
            error_msg = f"Thumbnail generation error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFmpegError(error_msg)
        finally:
            # Cleanup temporary file
            if local_path:
                self._cleanup_temp_file(local_path, is_temp)

    def probe_video(self, video_path: str) -> Dict[str, Any]:
        """
        Get full ffprobe JSON output with all video information

        Args:
            video_path: Path to video file or S3 URL

        Returns:
            Complete ffprobe output as dictionary

        Raises:
            FFprobeError: If probe fails
        """
        local_path = None
        is_temp = False

        try:
            logger.info(f"🔍 Probing video: {video_path}")

            # Get local path (download if S3)
            local_path, is_temp = self._get_local_path(video_path)

            # Build ffprobe command
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                local_path
            ]

            # Execute ffprobe
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,  # 30 seconds max
                check=True
            )

            # Parse JSON output
            probe_data = json.loads(result.stdout.decode())
            logger.info(f"✅ Video probed successfully")

            return probe_data

        except subprocess.CalledProcessError as e:
            error_msg = f"FFprobe failed: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFprobeError(error_msg)
        except subprocess.TimeoutExpired:
            error_msg = "FFprobe timed out (>30 seconds)"
            logger.error(f"❌ {error_msg}")
            raise FFprobeError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse ffprobe output: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFprobeError(error_msg)
        except Exception as e:
            error_msg = f"Video probe error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFprobeError(error_msg)
        finally:
            # Cleanup temporary file
            if local_path:
                self._cleanup_temp_file(local_path, is_temp)

    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """
        Extract essential video metadata (duration, resolution, codec, bitrate)

        Args:
            video_path: Path to video file or S3 URL

        Returns:
            Dictionary with video metadata:
            {
                'duration': float,  # Duration in seconds
                'duration_formatted': str,  # HH:MM:SS format
                'width': int,
                'height': int,
                'resolution': str,  # e.g., "1920x1080"
                'codec': str,  # Video codec name
                'audio_codec': str,  # Audio codec name
                'bitrate': int,  # Total bitrate in bps
                'bitrate_mbps': float,  # Bitrate in Mbps
                'fps': float,  # Frames per second
                'size': int,  # File size in bytes
                'size_mb': float,  # File size in MB
            }

        Raises:
            FFprobeError: If metadata extraction fails
        """
        try:
            # Get full probe data
            probe_data = self.probe_video(video_path)

            # Extract format info
            format_info = probe_data.get('format', {})

            # Find video and audio streams
            video_stream = None
            audio_stream = None

            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video' and not video_stream:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and not audio_stream:
                    audio_stream = stream

            if not video_stream:
                raise FFprobeError("No video stream found in file")

            # Extract duration
            duration = float(format_info.get('duration', 0))
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            # Extract resolution
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            resolution = f"{width}x{height}"

            # Extract codecs
            video_codec = video_stream.get('codec_name', 'unknown')
            audio_codec = audio_stream.get('codec_name', 'unknown') if audio_stream else 'none'

            # Extract bitrate
            bitrate = int(format_info.get('bit_rate', 0))
            bitrate_mbps = round(bitrate / 1_000_000, 2)

            # Extract FPS
            fps_str = video_stream.get('r_frame_rate', '0/1')
            fps_parts = fps_str.split('/')
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 0
            fps = round(fps, 2)

            # Extract file size
            file_size = int(format_info.get('size', 0))
            file_size_mb = round(file_size / (1024 * 1024), 2)

            metadata = {
                'duration': duration,
                'duration_formatted': duration_formatted,
                'width': width,
                'height': height,
                'resolution': resolution,
                'codec': video_codec,
                'audio_codec': audio_codec,
                'bitrate': bitrate,
                'bitrate_mbps': bitrate_mbps,
                'fps': fps,
                'size': file_size,
                'size_mb': file_size_mb,
            }

            logger.info(f"✅ Metadata extracted: {resolution}, {duration_formatted}, {bitrate_mbps}Mbps")
            return metadata

        except FFprobeError:
            raise
        except Exception as e:
            error_msg = f"Metadata extraction error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise FFprobeError(error_msg)

    def validate_video_file(self, video_path: str) -> bool:
        """
        Validate if file is a valid video file

        Args:
            video_path: Path to video file or S3 URL

        Returns:
            True if valid video file, False otherwise
        """
        try:
            logger.info(f"✓ Validating video file: {video_path}")

            # Try to probe the video
            probe_data = self.probe_video(video_path)

            # Check if there's at least one video stream
            has_video = False
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    has_video = True
                    break

            if not has_video:
                logger.warning(f"⚠️ File has no video stream: {video_path}")
                return False

            # Check duration
            format_info = probe_data.get('format', {})
            duration = float(format_info.get('duration', 0))

            if duration <= 0:
                logger.warning(f"⚠️ Video has invalid duration: {video_path}")
                return False

            logger.info(f"✅ Video file is valid: {video_path}")
            return True

        except (FFmpegError, FFprobeError) as e:
            logger.warning(f"⚠️ Video validation failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Video validation error: {str(e)}")
            return False

    def get_video_duration(self, video_path: str) -> float:
        """
        Get video duration in seconds (convenience method)

        Args:
            video_path: Path to video file or S3 URL

        Returns:
            Duration in seconds

        Raises:
            FFprobeError: If duration extraction fails
        """
        metadata = self.get_video_metadata(video_path)
        return metadata['duration']

    def get_video_resolution(self, video_path: str) -> Tuple[int, int]:
        """
        Get video resolution (convenience method)

        Args:
            video_path: Path to video file or S3 URL

        Returns:
            Tuple of (width, height)

        Raises:
            FFprobeError: If resolution extraction fails
        """
        metadata = self.get_video_metadata(video_path)
        return (metadata['width'], metadata['height'])


# Global ffmpeg service instance
ffmpeg_service = FFmpegService()
