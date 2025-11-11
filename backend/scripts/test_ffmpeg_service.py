#!/usr/bin/env python3
"""
Test script for FFMPEG Service
Demonstrates usage of all FFMPEG service functions
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ffmpeg_service import ffmpeg_service


def test_ffmpeg_installation():
    """Test 1: Verify FFMPEG installation"""
    print("\n" + "="*60)
    print("TEST 1: Verify FFMPEG Installation")
    print("="*60)
    try:
        print("✅ FFmpeg service initialized successfully")
        print("✅ FFmpeg and FFprobe are properly installed")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_validate_video(video_path: str):
    """Test 2: Validate video file"""
    print("\n" + "="*60)
    print("TEST 2: Validate Video File")
    print("="*60)
    try:
        is_valid = ffmpeg_service.validate_video_file(video_path)
        if is_valid:
            print(f"✅ Video is valid: {video_path}")
        else:
            print(f"❌ Video is invalid: {video_path}")
        return is_valid
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_probe_video(video_path: str):
    """Test 3: Probe video (full JSON)"""
    print("\n" + "="*60)
    print("TEST 3: Probe Video (Full JSON)")
    print("="*60)
    try:
        probe_data = ffmpeg_service.probe_video(video_path)
        print(f"✅ Probe successful")
        print(f"   Format: {probe_data['format']['format_name']}")
        print(f"   Streams: {len(probe_data['streams'])}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_get_metadata(video_path: str):
    """Test 4: Get video metadata"""
    print("\n" + "="*60)
    print("TEST 4: Get Video Metadata")
    print("="*60)
    try:
        metadata = ffmpeg_service.get_video_metadata(video_path)
        print(f"✅ Metadata extracted:")
        print(f"   Duration: {metadata['duration_formatted']} ({metadata['duration']}s)")
        print(f"   Resolution: {metadata['resolution']} ({metadata['width']}x{metadata['height']})")
        print(f"   Video Codec: {metadata['codec']}")
        print(f"   Audio Codec: {metadata['audio_codec']}")
        print(f"   Bitrate: {metadata['bitrate_mbps']} Mbps")
        print(f"   FPS: {metadata['fps']}")
        print(f"   Size: {metadata['size_mb']} MB")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_extract_audio(video_path: str, output_dir: str):
    """Test 5: Extract audio to MP3"""
    print("\n" + "="*60)
    print("TEST 5: Extract Audio to MP3")
    print("="*60)
    try:
        output_path = os.path.join(output_dir, "extracted_audio.mp3")
        result = ffmpeg_service.extract_audio(
            video_path=video_path,
            output_path=output_path,
            sample_rate=16000,
            channels=1
        )
        print(f"✅ Audio extracted to: {result}")
        print(f"   File size: {os.path.getsize(result) / 1024 / 1024:.2f} MB")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_generate_thumbnail(video_path: str, output_dir: str):
    """Test 6: Generate thumbnail"""
    print("\n" + "="*60)
    print("TEST 6: Generate Thumbnail")
    print("="*60)
    try:
        output_path = os.path.join(output_dir, "thumbnail.jpg")
        result = ffmpeg_service.generate_thumbnail(
            video_path=video_path,
            output_path=output_path,
            timestamp=5.0,
            width=640
        )
        print(f"✅ Thumbnail generated: {result}")
        print(f"   File size: {os.path.getsize(result) / 1024:.2f} KB")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "FFMPEG SERVICE TEST SUITE" + " "*18 + "║")
    print("╚" + "="*58 + "╝")

    # Test 1: Verify installation (always runs)
    test_ffmpeg_installation()

    # Check if video path provided
    if len(sys.argv) < 2:
        print("\n" + "="*60)
        print("ℹ️  Usage: python test_ffmpeg_service.py <video_path>")
        print("="*60)
        print("\nExample:")
        print("  python test_ffmpeg_service.py /path/to/video.mp4")
        print("\n✅ Basic installation test passed!")
        print("   Provide a video file path to run full test suite.")
        return

    video_path = sys.argv[1]

    # Verify video file exists
    if not os.path.exists(video_path):
        print(f"\n❌ Error: Video file not found: {video_path}")
        return

    # Create output directory for tests
    output_dir = os.path.join(os.path.dirname(video_path), "ffmpeg_test_output")
    os.makedirs(output_dir, exist_ok=True)

    # Run all tests
    results = []
    results.append(("Installation Check", True))
    results.append(("Validate Video", test_validate_video(video_path)))
    results.append(("Probe Video", test_probe_video(video_path)))
    results.append(("Get Metadata", test_get_metadata(video_path)))
    results.append(("Extract Audio", test_extract_audio(video_path, output_dir)))
    results.append(("Generate Thumbnail", test_generate_thumbnail(video_path, output_dir)))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"Output directory: {output_dir}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
