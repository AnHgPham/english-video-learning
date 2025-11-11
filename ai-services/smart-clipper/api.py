"""
Smart Clipper Service API

This service uses Google's Gemini AI to intelligently determine optimal clip boundaries
for educational video content. It analyzes context, semantic meaning, and timestamp
information to create coherent, meaningful video clips.

Features:
- AI-powered clip boundary detection
- Context-aware segmentation
- Natural language understanding
- Reasoning explanation for clip decisions
- Support for custom clip parameters
"""

import os
import logging
from typing import List, Optional, Dict, Any
from enum import Enum

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Smart Clipper Service",
    description="AI-powered intelligent video clip boundary detection using Gemini",
    version="1.0.0"
)

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info(f"Gemini configured with model: {GEMINI_MODEL}")
else:
    logger.warning("GEMINI_API_KEY not set - service will not function properly")


class ClipContext(str, Enum):
    """Context types for clip creation"""
    VOCABULARY = "vocabulary"  # Focus on vocabulary learning
    GRAMMAR = "grammar"  # Focus on grammar patterns
    CONVERSATION = "conversation"  # Natural conversation flow
    IDIOM = "idiom"  # Idiomatic expressions
    GENERAL = "general"  # General purpose clip


class WordTimestamp(BaseModel):
    """Word with timestamp information"""
    word: str = Field(..., description="The word text")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")


class ClipRequest(BaseModel):
    """Request model for clip boundary detection"""
    target_word: Optional[str] = Field(None, description="Target word or phrase to focus on")
    target_timestamp: float = Field(..., description="Timestamp around which to create clip (seconds)")
    context_words: List[WordTimestamp] = Field(..., description="Words with timestamps for context")
    context_type: ClipContext = Field(default=ClipContext.GENERAL, description="Type of clip context")
    min_duration: float = Field(default=3.0, description="Minimum clip duration in seconds")
    max_duration: float = Field(default=15.0, description="Maximum clip duration in seconds")
    prefer_complete_sentences: bool = Field(default=True, description="Prefer complete sentences")

    @validator('context_words')
    def validate_context(cls, v):
        if not v:
            raise ValueError("Context words cannot be empty")
        if len(v) < 3:
            raise ValueError("Need at least 3 words for context")
        return v

    @validator('target_timestamp')
    def validate_timestamp(cls, v):
        if v < 0:
            raise ValueError("Timestamp must be non-negative")
        return v


class ClipBoundary(BaseModel):
    """Output model for clip boundaries"""
    start_time: float = Field(..., description="Clip start time in seconds")
    end_time: float = Field(..., description="Clip end time in seconds")
    start_word_index: int = Field(..., description="Index of first word in clip")
    end_word_index: int = Field(..., description="Index of last word in clip")
    clip_text: str = Field(..., description="Full text of the clip")
    duration: float = Field(..., description="Clip duration in seconds")


class ClipResponse(BaseModel):
    """Response model for clip creation"""
    boundary: ClipBoundary = Field(..., description="Determined clip boundaries")
    reasoning: str = Field(..., description="AI reasoning for clip boundaries")
    confidence: float = Field(..., description="Confidence score (0-1)")
    context_type: str = Field(..., description="Context type used")
    includes_target: bool = Field(..., description="Whether clip includes target word/phrase")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    gemini_configured: bool
    model: str


def build_clip_prompt(request: ClipRequest) -> str:
    """
    Build prompt for Gemini to determine clip boundaries

    Args:
        request: Clip request with context

    Returns:
        Formatted prompt string
    """
    # Build context text with word indices
    context_text = []
    for i, word in enumerate(request.context_words):
        context_text.append(f"[{i}] {word.word} ({word.start:.2f}s - {word.end:.2f}s)")

    context_str = "\n".join(context_text)

    # Find target word index if specified
    target_info = ""
    if request.target_word:
        target_indices = [
            i for i, w in enumerate(request.context_words)
            if request.target_word.lower() in w.word.lower()
        ]
        if target_indices:
            target_info = f"\nTarget word '{request.target_word}' appears at indices: {target_indices}"
        else:
            target_info = f"\nTarget word '{request.target_word}' should be near timestamp {request.target_timestamp}s"

    prompt = f"""You are an expert video editor for educational content. Your task is to determine optimal clip boundaries.

CONTEXT TYPE: {request.context_type.value}

TARGET TIMESTAMP: {request.target_timestamp}s{target_info}

CONSTRAINTS:
- Minimum duration: {request.min_duration}s
- Maximum duration: {request.max_duration}s
- Prefer complete sentences: {request.prefer_complete_sentences}

WORD TIMELINE:
{context_str}

FULL TEXT:
{' '.join([w.word for w in request.context_words])}

TASK:
Determine the optimal start and end word indices for a clip that:
1. Centers around the target timestamp ({request.target_timestamp}s)
2. Maintains semantic coherence and natural flow
3. Provides educational value for {request.context_type.value} learning
4. Respects the duration constraints
5. {"Includes complete sentences when possible" if request.prefer_complete_sentences else "Can break at phrase boundaries"}

Respond in the following JSON format:
{{
    "start_index": <word index>,
    "end_index": <word index>,
    "reasoning": "<explanation of why these boundaries were chosen>",
    "confidence": <0.0 to 1.0>
}}

Consider:
- Natural speech boundaries (pauses, sentence endings)
- Semantic completeness (full thoughts/ideas)
- Educational value (clear examples, context)
- Engagement (interesting, not too long)
"""

    return prompt


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def call_gemini(prompt: str) -> Dict[str, Any]:
    """
    Call Gemini API with retry logic

    Args:
        prompt: Prompt to send to Gemini

    Returns:
        Parsed JSON response

    Raises:
        Exception: If API call fails after retries
    """
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)

        # Configure safety settings
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                top_p=0.8,
                top_k=40,
            )
        )

        # Extract text and parse JSON
        result_text = response.text.strip()

        # Clean up markdown code blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]

        result_text = result_text.strip()

        # Parse JSON
        import json
        result = json.loads(result_text)

        return result

    except Exception as e:
        logger.error(f"Gemini API call failed: {str(e)}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        Service status
    """
    return HealthResponse(
        status="healthy" if GEMINI_API_KEY else "degraded",
        gemini_configured=bool(GEMINI_API_KEY),
        model=GEMINI_MODEL
    )


@app.post("/clip", response_model=ClipResponse)
async def create_clip(request: ClipRequest):
    """
    Determine optimal clip boundaries using AI

    Args:
        request: Clip request with context and constraints

    Returns:
        Clip boundaries with reasoning

    Raises:
        HTTPException: If clip creation fails
    """
    try:
        if not GEMINI_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Gemini API key not configured"
            )

        logger.info(
            f"Creating clip: target={request.target_word}, "
            f"timestamp={request.target_timestamp}, context={request.context_type}"
        )

        # Build prompt
        prompt = build_clip_prompt(request)

        # Call Gemini
        logger.info("Calling Gemini API...")
        result = call_gemini(prompt)

        # Extract results
        start_idx = result.get("start_index", 0)
        end_idx = result.get("end_index", len(request.context_words) - 1)
        reasoning = result.get("reasoning", "No reasoning provided")
        confidence = result.get("confidence", 0.7)

        # Validate indices
        start_idx = max(0, min(start_idx, len(request.context_words) - 1))
        end_idx = max(start_idx, min(end_idx, len(request.context_words) - 1))

        # Build boundary
        clip_words = request.context_words[start_idx:end_idx + 1]
        clip_text = " ".join([w.word for w in clip_words])
        start_time = clip_words[0].start
        end_time = clip_words[-1].end
        duration = end_time - start_time

        # Check if target is included
        includes_target = False
        if request.target_word:
            includes_target = any(
                request.target_word.lower() in w.word.lower()
                for w in clip_words
            )
        else:
            # Check if target timestamp is within clip
            includes_target = start_time <= request.target_timestamp <= end_time

        boundary = ClipBoundary(
            start_time=start_time,
            end_time=end_time,
            start_word_index=start_idx,
            end_word_index=end_idx,
            clip_text=clip_text,
            duration=duration
        )

        logger.info(
            f"Clip created: {start_time:.2f}s - {end_time:.2f}s "
            f"({duration:.2f}s, {len(clip_words)} words)"
        )

        return ClipResponse(
            boundary=boundary,
            reasoning=reasoning,
            confidence=confidence,
            context_type=request.context_type.value,
            includes_target=includes_target
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clip creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Clip creation failed: {str(e)}")


@app.post("/clip/simple")
async def create_simple_clip(
    target_timestamp: float,
    words: List[WordTimestamp],
    duration: float = 10.0
):
    """
    Create a simple clip without AI (fallback method)

    Args:
        target_timestamp: Center timestamp
        words: Words with timestamps
        duration: Desired duration

    Returns:
        Simple clip boundaries
    """
    try:
        # Find words around target timestamp
        half_duration = duration / 2

        # Find start and end indices
        start_idx = 0
        end_idx = len(words) - 1

        for i, word in enumerate(words):
            if word.start <= target_timestamp - half_duration:
                start_idx = i
            if word.end >= target_timestamp + half_duration:
                end_idx = i
                break

        clip_words = words[start_idx:end_idx + 1]
        clip_text = " ".join([w.word for w in clip_words])

        boundary = ClipBoundary(
            start_time=clip_words[0].start,
            end_time=clip_words[-1].end,
            start_word_index=start_idx,
            end_word_index=end_idx,
            clip_text=clip_text,
            duration=clip_words[-1].end - clip_words[0].start
        )

        return ClipResponse(
            boundary=boundary,
            reasoning="Simple time-based clipping without AI analysis",
            confidence=0.5,
            context_type="general",
            includes_target=True
        )

    except Exception as e:
        logger.error(f"Simple clip creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Smart Clipper Service",
        "version": "1.0.0",
        "ai_model": GEMINI_MODEL,
        "context_types": [c.value for c in ClipContext],
        "endpoints": {
            "clip": "/clip",
            "simple_clip": "/clip/simple",
            "health": "/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
