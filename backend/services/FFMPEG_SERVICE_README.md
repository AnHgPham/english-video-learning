# FFMPEG Service Documentation

## Overview

The FFMPEG Service (`ffmpeg_service.py`) provides comprehensive video processing utilities using FFMPEG and FFprobe. It supports both local file processing and automatic S3/MinIO downloads.

**File Location**: `/home/user/english-video-learning/backend/services/ffmpeg_service.py`

---

## Features

- ✅ **Audio Extraction**: Extract audio to MP3 format with customizable sample rate and channels
- ✅ **Thumbnail Generation**: Extract video frames as JPG thumbnails
- ✅ **Metadata Extraction**: Get duration, resolution, codec, bitrate, and more
- ✅ **Video Probing**: Full ffprobe JSON output for detailed analysis
- ✅ **Video Validation**: Check if file is a valid video
- ✅ **S3/MinIO Support**: Automatically download from S3/MinIO if needed
- ✅ **Error Handling**: Comprehensive error handling with custom exceptions
- ✅ **Logging**: Detailed logging for all operations
- ✅ **Type Hints**: Full type annotations for better IDE support

---

## Installation Requirements

### System Dependencies

```bash
# Install FFMPEG and FFprobe
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg

# macOS
brew install ffmpeg

# Verify installation
ffmpeg -version
ffprobe -version
```

### Python Dependencies

Already included in `requirements.txt`:
- subprocess (built-in)
- json (built-in)
- logging (built-in)
- tempfile (built-in)

---

## Quick Start

```python
from services.ffmpeg_service import ffmpeg_service

# 1. Validate video file
is_valid = ffmpeg_service.validate_video_file("/path/to/video.mp4")
print(f"Valid: {is_valid}")

# 2. Get metadata
metadata = ffmpeg_service.get_video_metadata("/path/to/video.mp4")
print(f"Duration: {metadata['duration_formatted']}")
print(f"Resolution: {metadata['resolution']}")
print(f"Codec: {metadata['codec']}")

# 3. Extract audio
audio_path = ffmpeg_service.extract_audio(
    video_path="/path/to/video.mp4",
    output_path="/path/to/output.mp3",
    sample_rate=16000,  # 16kHz for speech recognition
    channels=1  # Mono
)

# 4. Generate thumbnail
thumb_path = ffmpeg_service.generate_thumbnail(
    video_path="/path/to/video.mp4",
    output_path="/path/to/thumbnail.jpg",
    timestamp=5.0,  # 5 seconds into video
    width=640  # Auto-scaled height
)
```

---

## API Reference

### Class: `FFmpegService`

The main service class providing all FFMPEG operations.

#### Global Instance

```python
from services.ffmpeg_service import ffmpeg_service
```

A global instance `ffmpeg_service` is automatically created and can be imported directly.

---

### Methods

#### `extract_audio()`

Extract audio from video file to MP3 format.

```python
def extract_audio(
    self,
    video_path: str,
    output_path: str,
    sample_rate: int = 16000,
    channels: int = 1
) -> str
```

**Parameters:**
- `video_path` (str): Path to video file or S3 URL
- `output_path` (str): Path for output MP3 file
- `sample_rate` (int): Audio sample rate in Hz (default: 16000 for speech recognition)
- `channels` (int): Number of channels - 1=mono, 2=stereo (default: 1)

**Returns:**
- `str`: Path to extracted audio file

**Raises:**
- `FFmpegError`: If extraction fails

**Example:**

```python
# Extract mono audio at 16kHz (optimal for Whisper/speech recognition)
audio_path = ffmpeg_service.extract_audio(
    video_path="/videos/lesson1.mp4",
    output_path="/audio/lesson1.mp3",
    sample_rate=16000,
    channels=1
)

# Extract stereo audio at 44.1kHz (CD quality)
audio_path = ffmpeg_service.extract_audio(
    video_path="/videos/music_video.mp4",
    output_path="/audio/music.mp3",
    sample_rate=44100,
    channels=2
)

# Works with S3 URLs too
audio_path = ffmpeg_service.extract_audio(
    video_path="http://localhost:9000/videos/lesson1.mp4",
    output_path="/tmp/audio.mp3"
)
```

---

#### `generate_thumbnail()`

Generate thumbnail image from video at specified timestamp.

```python
def generate_thumbnail(
    self,
    video_path: str,
    output_path: str,
    timestamp: float = 5.0,
    width: Optional[int] = None,
    height: Optional[int] = None,
    quality: int = 2
) -> str
```

**Parameters:**
- `video_path` (str): Path to video file or S3 URL
- `output_path` (str): Path for output JPG file
- `timestamp` (float): Time in seconds to extract frame (default: 5.0)
- `width` (int, optional): Output width in pixels (maintains aspect ratio)
- `height` (int, optional): Output height in pixels (maintains aspect ratio)
- `quality` (int): JPEG quality 2-31 (lower is better, default: 2)

**Returns:**
- `str`: Path to generated thumbnail

**Raises:**
- `FFmpegError`: If thumbnail generation fails

**Example:**

```python
# Basic thumbnail at 5 seconds
thumb = ffmpeg_service.generate_thumbnail(
    video_path="/videos/lesson1.mp4",
    output_path="/thumbnails/lesson1.jpg"
)

# Thumbnail at specific timestamp with custom width
thumb = ffmpeg_service.generate_thumbnail(
    video_path="/videos/lesson1.mp4",
    output_path="/thumbnails/lesson1_custom.jpg",
    timestamp=30.5,  # 30.5 seconds into video
    width=1280,  # HD width, height auto-scaled
    quality=2  # High quality
)

# Multiple thumbnails for preview
for i, timestamp in enumerate([5, 15, 30, 60]):
    ffmpeg_service.generate_thumbnail(
        video_path="/videos/lesson1.mp4",
        output_path=f"/thumbnails/lesson1_preview_{i}.jpg",
        timestamp=timestamp,
        width=320  # Small preview size
    )
```

---

#### `get_video_metadata()`

Extract essential video metadata.

```python
def get_video_metadata(self, video_path: str) -> Dict[str, Any]
```

**Parameters:**
- `video_path` (str): Path to video file or S3 URL

**Returns:**
- `Dict[str, Any]`: Dictionary with video metadata

**Metadata Fields:**
- `duration` (float): Duration in seconds
- `duration_formatted` (str): Duration in HH:MM:SS format
- `width` (int): Video width in pixels
- `height` (int): Video height in pixels
- `resolution` (str): Resolution string (e.g., "1920x1080")
- `codec` (str): Video codec name (e.g., "h264")
- `audio_codec` (str): Audio codec name (e.g., "aac")
- `bitrate` (int): Total bitrate in bps
- `bitrate_mbps` (float): Bitrate in Mbps
- `fps` (float): Frames per second
- `size` (int): File size in bytes
- `size_mb` (float): File size in MB

**Raises:**
- `FFprobeError`: If metadata extraction fails

**Example:**

```python
metadata = ffmpeg_service.get_video_metadata("/videos/lesson1.mp4")

print(f"Duration: {metadata['duration_formatted']}")  # "00:15:30"
print(f"Resolution: {metadata['resolution']}")  # "1920x1080"
print(f"Size: {metadata['size_mb']} MB")  # "245.67 MB"
print(f"Codec: {metadata['codec']}")  # "h264"
print(f"FPS: {metadata['fps']}")  # 30.0

# Use metadata to validate video quality
if metadata['width'] < 1280:
    print("⚠️ Low resolution video")

if metadata['duration'] > 3600:
    print("⚠️ Video longer than 1 hour")

if metadata['bitrate_mbps'] < 1.0:
    print("⚠️ Low bitrate - quality may be poor")
```

---

#### `probe_video()`

Get full ffprobe JSON output with all video information.

```python
def probe_video(self, video_path: str) -> Dict[str, Any]
```

**Parameters:**
- `video_path` (str): Path to video file or S3 URL

**Returns:**
- `Dict[str, Any]`: Complete ffprobe output as dictionary

**Raises:**
- `FFprobeError`: If probe fails

**Example:**

```python
probe_data = ffmpeg_service.probe_video("/videos/lesson1.mp4")

# Access format information
print(f"Format: {probe_data['format']['format_name']}")
print(f"Duration: {probe_data['format']['duration']}")

# Iterate through streams
for stream in probe_data['streams']:
    codec_type = stream['codec_type']
    codec_name = stream['codec_name']
    print(f"Stream: {codec_type} - {codec_name}")

    if codec_type == 'video':
        print(f"  Resolution: {stream['width']}x{stream['height']}")
        print(f"  FPS: {stream['r_frame_rate']}")
    elif codec_type == 'audio':
        print(f"  Sample Rate: {stream.get('sample_rate', 'N/A')}")
        print(f"  Channels: {stream.get('channels', 'N/A')}")
```

---

#### `validate_video_file()`

Validate if file is a valid video file.

```python
def validate_video_file(self, video_path: str) -> bool
```

**Parameters:**
- `video_path` (str): Path to video file or S3 URL

**Returns:**
- `bool`: True if valid video file, False otherwise

**Example:**

```python
# Validate before processing
if ffmpeg_service.validate_video_file("/uploads/video.mp4"):
    print("✅ Valid video - processing...")
    metadata = ffmpeg_service.get_video_metadata("/uploads/video.mp4")
else:
    print("❌ Invalid video file")

# Validate user uploads
def process_upload(file_path: str):
    if not ffmpeg_service.validate_video_file(file_path):
        raise ValueError("Invalid video file uploaded")

    # Continue processing...
    return ffmpeg_service.extract_audio(file_path, "/audio/output.mp3")
```

---

#### `get_video_duration()` (Convenience Method)

Get video duration in seconds.

```python
def get_video_duration(self, video_path: str) -> float
```

**Parameters:**
- `video_path` (str): Path to video file or S3 URL

**Returns:**
- `float`: Duration in seconds

**Example:**

```python
duration = ffmpeg_service.get_video_duration("/videos/lesson1.mp4")
print(f"Video is {duration} seconds long")

# Check if video is too long
MAX_DURATION = 3600  # 1 hour
if duration > MAX_DURATION:
    raise ValueError(f"Video too long: {duration}s (max: {MAX_DURATION}s)")
```

---

#### `get_video_resolution()` (Convenience Method)

Get video resolution as tuple.

```python
def get_video_resolution(self, video_path: str) -> Tuple[int, int]
```

**Parameters:**
- `video_path` (str): Path to video file or S3 URL

**Returns:**
- `Tuple[int, int]`: Width and height in pixels

**Example:**

```python
width, height = ffmpeg_service.get_video_resolution("/videos/lesson1.mp4")
print(f"Resolution: {width}x{height}")

# Determine quality tier
if width >= 1920 and height >= 1080:
    quality = "HD (1080p or higher)"
elif width >= 1280 and height >= 720:
    quality = "HD (720p)"
else:
    quality = "SD"

print(f"Quality: {quality}")
```

---

## Error Handling

The service defines two custom exceptions:

### `FFmpegError`

Raised when FFMPEG operations fail (audio extraction, thumbnail generation).

```python
from services.ffmpeg_service import FFmpegError

try:
    ffmpeg_service.extract_audio("/invalid/path.mp4", "/output.mp3")
except FFmpegError as e:
    logger.error(f"Audio extraction failed: {e}")
    # Handle error appropriately
```

### `FFprobeError`

Raised when FFprobe operations fail (probing, metadata extraction).

```python
from services.ffmpeg_service import FFprobeError

try:
    metadata = ffmpeg_service.get_video_metadata("/corrupted/video.mp4")
except FFprobeError as e:
    logger.error(f"Failed to get metadata: {e}")
    # Handle error appropriately
```

---

## S3/MinIO Support

The service automatically handles S3/MinIO URLs:

```python
# Works with local files
ffmpeg_service.extract_audio(
    video_path="/local/video.mp4",
    output_path="/output/audio.mp3"
)

# Works with MinIO URLs
ffmpeg_service.extract_audio(
    video_path="http://localhost:9000/videos/lesson1.mp4",
    output_path="/output/audio.mp3"
)

# Works with AWS S3 URLs
ffmpeg_service.extract_audio(
    video_path="https://my-bucket.s3.us-east-1.amazonaws.com/videos/lesson1.mp4",
    output_path="/output/audio.mp3"
)
```

**How it works:**
1. Service detects S3/MinIO URLs automatically
2. Downloads file to temporary location using presigned URL
3. Processes the local temporary file
4. Automatically cleans up temporary file after processing

---

## Usage Examples

### Example 1: Video Upload Processing Pipeline

```python
from services.ffmpeg_service import ffmpeg_service
import os

def process_video_upload(video_path: str, video_id: int):
    """Complete video processing pipeline"""

    # 1. Validate video
    if not ffmpeg_service.validate_video_file(video_path):
        raise ValueError("Invalid video file")

    # 2. Get metadata
    metadata = ffmpeg_service.get_video_metadata(video_path)

    # 3. Extract audio for transcription
    audio_path = f"/audio/{video_id}.mp3"
    ffmpeg_service.extract_audio(
        video_path=video_path,
        output_path=audio_path,
        sample_rate=16000,  # Optimal for Whisper
        channels=1
    )

    # 4. Generate thumbnails
    thumbnail_path = f"/thumbnails/{video_id}.jpg"
    ffmpeg_service.generate_thumbnail(
        video_path=video_path,
        output_path=thumbnail_path,
        timestamp=5.0,
        width=1280
    )

    # 5. Generate preview thumbnails (every 10 seconds)
    duration = metadata['duration']
    preview_timestamps = range(0, int(duration), 10)

    for i, timestamp in enumerate(preview_timestamps):
        if timestamp >= duration:
            break
        preview_path = f"/thumbnails/{video_id}_preview_{i}.jpg"
        ffmpeg_service.generate_thumbnail(
            video_path=video_path,
            output_path=preview_path,
            timestamp=timestamp,
            width=320
        )

    return {
        'metadata': metadata,
        'audio_path': audio_path,
        'thumbnail_path': thumbnail_path,
        'preview_count': len(preview_timestamps)
    }
```

### Example 2: Video Quality Checker

```python
def check_video_quality(video_path: str) -> dict:
    """Check if video meets quality standards"""

    metadata = ffmpeg_service.get_video_metadata(video_path)

    issues = []
    warnings = []

    # Check resolution
    if metadata['width'] < 1280 or metadata['height'] < 720:
        issues.append("Resolution below 720p")

    # Check duration
    if metadata['duration'] < 60:
        warnings.append("Video shorter than 1 minute")
    elif metadata['duration'] > 3600:
        warnings.append("Video longer than 1 hour")

    # Check bitrate
    if metadata['bitrate_mbps'] < 1.0:
        issues.append("Bitrate too low (< 1 Mbps)")

    # Check codec
    if metadata['codec'] not in ['h264', 'h265', 'vp9']:
        warnings.append(f"Uncommon codec: {metadata['codec']}")

    # Check audio
    if metadata['audio_codec'] == 'none':
        issues.append("No audio track")

    return {
        'quality_score': 100 - (len(issues) * 25) - (len(warnings) * 10),
        'issues': issues,
        'warnings': warnings,
        'metadata': metadata
    }
```

### Example 3: Batch Processing

```python
import os
from pathlib import Path

def batch_process_videos(input_dir: str, output_dir: str):
    """Process all videos in directory"""

    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']

    for video_file in Path(input_dir).rglob('*'):
        if video_file.suffix.lower() not in video_extensions:
            continue

        video_path = str(video_file)
        video_name = video_file.stem

        print(f"Processing: {video_name}")

        try:
            # Validate
            if not ffmpeg_service.validate_video_file(video_path):
                print(f"  ❌ Invalid video: {video_name}")
                continue

            # Extract audio
            audio_path = os.path.join(output_dir, 'audio', f"{video_name}.mp3")
            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
            ffmpeg_service.extract_audio(video_path, audio_path)
            print(f"  ✅ Audio extracted")

            # Generate thumbnail
            thumb_path = os.path.join(output_dir, 'thumbnails', f"{video_name}.jpg")
            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
            ffmpeg_service.generate_thumbnail(video_path, thumb_path)
            print(f"  ✅ Thumbnail generated")

        except Exception as e:
            print(f"  ❌ Error: {e}")
```

---

## Testing

A comprehensive test script is provided:

```bash
# Run basic installation test
cd /home/user/english-video-learning/backend
python scripts/test_ffmpeg_service.py

# Run full test suite with a video file
python scripts/test_ffmpeg_service.py /path/to/test/video.mp4
```

The test script will:
1. ✅ Verify FFMPEG installation
2. ✅ Validate video file
3. ✅ Probe video (full JSON)
4. ✅ Extract metadata
5. ✅ Extract audio to MP3
6. ✅ Generate thumbnail

---

## Logging

The service uses Python's logging module:

```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# Now all operations will be logged
ffmpeg_service.extract_audio("/video.mp4", "/audio.mp3")
# Output: 🎵 Extracting audio from: /video.mp4
# Output: ✅ Audio extracted successfully: /audio.mp3 (12345678 bytes)
```

**Log Levels:**
- `INFO`: Operation starts, completions, and results
- `WARNING`: Non-fatal issues (cleanup failures, quality warnings)
- `ERROR`: Operation failures and exceptions
- `DEBUG`: Detailed operation info (temp file paths, etc.)

---

## Performance Considerations

### Timeouts

Operations have built-in timeouts to prevent hanging:
- Audio extraction: 10 minutes
- Thumbnail generation: 1 minute
- Video probing: 30 seconds
- S3 downloads: 5 minutes

### Temporary Files

When processing S3/MinIO URLs:
- Files are downloaded to system temp directory
- Automatically cleaned up after processing
- Cleanup happens even if operation fails

### Memory Usage

- Subprocess-based: FFMPEG runs as separate process
- Minimal memory overhead in Python
- Large files handled efficiently by FFMPEG

---

## Integration with Celery

For background processing:

```python
from celery import shared_task
from services.ffmpeg_service import ffmpeg_service

@shared_task
def process_video_async(video_id: int, video_path: str):
    """Process video in background"""

    try:
        # Extract audio
        audio_path = f"/audio/{video_id}.mp3"
        ffmpeg_service.extract_audio(video_path, audio_path)

        # Generate thumbnail
        thumb_path = f"/thumbnails/{video_id}.jpg"
        ffmpeg_service.generate_thumbnail(video_path, thumb_path)

        # Get metadata
        metadata = ffmpeg_service.get_video_metadata(video_path)

        return {
            'status': 'success',
            'audio_path': audio_path,
            'thumbnail_path': thumb_path,
            'metadata': metadata
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
```

---

## Troubleshooting

### FFMPEG Not Found

```
FFmpegError: FFMPEG or FFprobe not found in system PATH
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Verify
ffmpeg -version
```

### Invalid Video File

```
FFmpegError: Video file not found: /path/to/video.mp4
```

**Solution:**
- Check file path is correct
- Check file permissions
- Verify file exists with: `ls -la /path/to/video.mp4`

### S3 Download Failed

```
FFmpegError: Failed to download from S3
```

**Solution:**
- Check S3/MinIO credentials in `.env`
- Verify bucket and object key are correct
- Check network connectivity
- Ensure storage service is properly configured

### Operation Timeout

```
FFmpegError: Audio extraction timed out (>10 minutes)
```

**Solution:**
- Video file may be corrupted
- File may be too large
- Increase timeout in code if needed for large files

---

## Additional Resources

- [FFMPEG Documentation](https://ffmpeg.org/documentation.html)
- [FFprobe Documentation](https://ffmpeg.org/ffprobe.html)
- [FFMPEG Filters](https://ffmpeg.org/ffmpeg-filters.html)

---

## Support

For issues or questions:
1. Check logs for detailed error messages
2. Verify FFMPEG installation
3. Test with sample video file
4. Run test script for diagnostics

---

**Created**: 2025-11-11
**Version**: 1.0.0
**Author**: English Video Learning Platform Team
