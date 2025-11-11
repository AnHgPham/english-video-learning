"""
WhisperX Transcription Service API

This service provides speech-to-text transcription with word-level timestamps
using WhisperX, an enhanced version of OpenAI's Whisper model.

Features:
- GPU-accelerated transcription
- Word-level timestamp alignment
- Multiple language support
- Automatic language detection
- Speaker diarization support
"""

import os
import tempfile
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

import whisperx
import torch
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import aiofiles

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="WhisperX Transcription Service",
    description="GPU-accelerated speech-to-text transcription with word-level timestamps",
    version="1.0.0"
)

# Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
BATCH_SIZE = 16
MODEL_NAME = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large-v2

# Global model cache
_model_cache = {}
_align_model_cache = {}


class TranscriptionWord(BaseModel):
    """Model for a single transcribed word with timestamp"""
    word: str = Field(..., description="The transcribed word")
    start: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")
    score: Optional[float] = Field(None, description="Confidence score")


class TranscriptionSegment(BaseModel):
    """Model for a transcription segment"""
    text: str = Field(..., description="Segment text")
    start: float = Field(..., description="Segment start time in seconds")
    end: float = Field(..., description="Segment end time in seconds")
    words: List[TranscriptionWord] = Field(default_factory=list, description="Word-level timestamps")


class TranscriptionResponse(BaseModel):
    """Response model for transcription"""
    language: str = Field(..., description="Detected or specified language")
    segments: List[TranscriptionSegment] = Field(..., description="Transcription segments")
    text: str = Field(..., description="Full transcription text")
    duration: float = Field(..., description="Audio duration in seconds")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    device: str
    model: str
    cuda_available: bool


def load_whisper_model(model_name: str = MODEL_NAME):
    """
    Load WhisperX model with caching

    Args:
        model_name: Name of the Whisper model to load

    Returns:
        Loaded WhisperX model
    """
    if model_name not in _model_cache:
        logger.info(f"Loading WhisperX model: {model_name} on {DEVICE}")
        try:
            model = whisperx.load_model(
                model_name,
                device=DEVICE,
                compute_type=COMPUTE_TYPE
            )
            _model_cache[model_name] = model
            logger.info(f"Model {model_name} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    return _model_cache[model_name]


def load_align_model(language: str):
    """
    Load alignment model for word-level timestamps

    Args:
        language: Language code for alignment model

    Returns:
        Alignment model and metadata
    """
    if language not in _align_model_cache:
        logger.info(f"Loading alignment model for language: {language}")
        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=language,
                device=DEVICE
            )
            _align_model_cache[language] = (model_a, metadata)
            logger.info(f"Alignment model for {language} loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load alignment model for {language}: {str(e)}")
            # Return None if alignment model fails - we'll continue without word alignment
            return None, None

    return _align_model_cache[language]


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        System status and configuration
    """
    return HealthResponse(
        status="healthy",
        device=DEVICE,
        model=MODEL_NAME,
        cuda_available=torch.cuda.is_available()
    )


@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    language: Optional[str] = Form(None, description="Language code (e.g., 'en', 'vi'). Auto-detect if not provided"),
    model: Optional[str] = Form(MODEL_NAME, description="Whisper model to use"),
    enable_alignment: bool = Form(True, description="Enable word-level timestamp alignment")
):
    """
    Transcribe audio file with word-level timestamps

    Args:
        audio: Audio file (mp3, wav, m4a, etc.)
        language: Optional language code. If not provided, language will be auto-detected
        model: Whisper model to use (tiny, base, small, medium, large-v2)
        enable_alignment: Whether to perform word-level alignment

    Returns:
        Transcription with word-level timestamps

    Raises:
        HTTPException: If transcription fails
    """
    temp_file_path = None

    try:
        # Validate file
        if not audio.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Save uploaded file to temporary location
        suffix = Path(audio.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            content = await audio.read()
            await aiofiles.open(temp_file_path, 'wb').write(content)

        logger.info(f"Processing audio file: {audio.filename} (size: {len(content)} bytes)")

        # Load model
        whisper_model = load_whisper_model(model)

        # Transcribe
        logger.info("Starting transcription...")
        result = whisper_model.transcribe(
            temp_file_path,
            batch_size=BATCH_SIZE,
            language=language
        )

        detected_language = result.get("language", language or "unknown")
        logger.info(f"Transcription complete. Detected language: {detected_language}")

        # Perform word-level alignment if enabled
        if enable_alignment:
            logger.info("Performing word-level alignment...")
            align_model, metadata = load_align_model(detected_language)

            if align_model and metadata:
                result = whisperx.align(
                    result["segments"],
                    align_model,
                    metadata,
                    temp_file_path,
                    DEVICE,
                    return_char_alignments=False
                )
                logger.info("Word-level alignment complete")
            else:
                logger.warning("Alignment model not available, skipping word alignment")
                result = {"segments": result["segments"]}
        else:
            result = {"segments": result["segments"]}

        # Process segments and extract word-level timestamps
        segments = []
        full_text = []

        for seg in result["segments"]:
            words = []

            # Extract word-level timestamps if available
            if "words" in seg:
                for word_info in seg["words"]:
                    words.append(TranscriptionWord(
                        word=word_info.get("word", ""),
                        start=word_info.get("start", 0.0),
                        end=word_info.get("end", 0.0),
                        score=word_info.get("score")
                    ))

            segment = TranscriptionSegment(
                text=seg["text"].strip(),
                start=seg["start"],
                end=seg["end"],
                words=words
            )
            segments.append(segment)
            full_text.append(seg["text"].strip())

        # Calculate duration from last segment
        duration = segments[-1].end if segments else 0.0

        response = TranscriptionResponse(
            language=detected_language,
            segments=segments,
            text=" ".join(full_text),
            duration=duration
        )

        logger.info(f"Transcription successful. Duration: {duration}s, Segments: {len(segments)}")
        return response

    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "WhisperX Transcription Service",
        "version": "1.0.0",
        "endpoints": {
            "transcribe": "/transcribe",
            "health": "/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
