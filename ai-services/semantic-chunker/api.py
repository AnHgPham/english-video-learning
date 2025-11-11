"""
Semantic Chunker Service API

This service intelligently chunks transcribed text into semantic units (sentences, phrases)
while preserving word-level timestamps. It uses NLP techniques to identify natural
breaking points in speech for better learning experience.

Features:
- Sentence boundary detection
- Semantic phrase chunking
- Timestamp preservation
- Multi-language support
- Configurable chunk size limits
"""

import logging
from typing import List, Optional, Dict, Any
from enum import Enum

import spacy
import nltk
from nltk.tokenize import sent_tokenize
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
    title="Semantic Chunker Service",
    description="Intelligent text chunking with semantic understanding and timestamp preservation",
    version="1.0.0"
)

# Global model cache
_nlp_models = {}


class ChunkingStrategy(str, Enum):
    """Available chunking strategies"""
    SENTENCE = "sentence"  # Break by sentences
    SEMANTIC = "semantic"  # Semantic phrase boundaries
    HYBRID = "hybrid"  # Combination of sentence and semantic
    FIXED_DURATION = "fixed_duration"  # Fixed time duration chunks


class WordInput(BaseModel):
    """Input model for a single word with timestamp"""
    word: str = Field(..., description="The word text")
    start: float = Field(..., description="Start timestamp in seconds")
    end: float = Field(..., description="End timestamp in seconds")
    score: Optional[float] = Field(None, description="Confidence score")


class ChunkRequest(BaseModel):
    """Request model for chunking"""
    words: List[WordInput] = Field(..., description="Array of words with timestamps")
    language: str = Field(default="en", description="Language code (en, vi, etc.)")
    strategy: ChunkingStrategy = Field(default=ChunkingStrategy.HYBRID, description="Chunking strategy")
    max_duration: Optional[float] = Field(default=10.0, description="Maximum chunk duration in seconds")
    min_duration: Optional[float] = Field(default=2.0, description="Minimum chunk duration in seconds")
    max_words: Optional[int] = Field(default=15, description="Maximum words per chunk")

    @validator('words')
    def validate_words(cls, v):
        if not v:
            raise ValueError("Words array cannot be empty")
        return v


class ChunkOutput(BaseModel):
    """Output model for a single chunk"""
    text: str = Field(..., description="Chunk text")
    start: float = Field(..., description="Chunk start timestamp")
    end: float = Field(..., description="Chunk end timestamp")
    words: List[WordInput] = Field(..., description="Words in this chunk")
    word_count: int = Field(..., description="Number of words in chunk")
    duration: float = Field(..., description="Duration in seconds")


class ChunkResponse(BaseModel):
    """Response model for chunking"""
    chunks: List[ChunkOutput] = Field(..., description="Array of semantic chunks")
    total_chunks: int = Field(..., description="Total number of chunks")
    total_duration: float = Field(..., description="Total duration in seconds")
    strategy_used: str = Field(..., description="Chunking strategy that was used")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    models_loaded: List[str]
    nltk_available: bool


def load_spacy_model(language: str = "en"):
    """
    Load spaCy model for the specified language

    Args:
        language: Language code

    Returns:
        Loaded spaCy model
    """
    if language not in _nlp_models:
        try:
            if language == "en":
                model_name = "en_core_web_sm"
            elif language == "vi":
                model_name = "vi_core_news_lg"
            else:
                model_name = "xx_ent_wiki_sm"  # Multilingual model

            logger.info(f"Loading spaCy model: {model_name}")
            nlp = spacy.load(model_name)
            _nlp_models[language] = nlp
            logger.info(f"Model {model_name} loaded successfully")

        except Exception as e:
            logger.warning(f"Failed to load model for {language}: {str(e)}, using basic tokenizer")
            # Fallback to basic English model
            try:
                nlp = spacy.load("en_core_web_sm")
                _nlp_models[language] = nlp
            except:
                raise HTTPException(status_code=500, detail=f"Failed to load NLP model: {str(e)}")

    return _nlp_models[language]


def chunk_by_sentences(text: str, words: List[WordInput], language: str = "en") -> List[List[WordInput]]:
    """
    Chunk words by sentence boundaries

    Args:
        text: Full text
        words: List of words with timestamps
        language: Language code

    Returns:
        List of word groups representing sentences
    """
    try:
        # Use NLTK for sentence tokenization
        sentences = sent_tokenize(text, language='english' if language == 'en' else language)

        if not sentences:
            return [words]

        chunks = []
        word_idx = 0
        word_list = list(words)

        for sentence in sentences:
            sentence_words = []
            sentence_text = sentence.strip()

            # Match words to sentences
            while word_idx < len(word_list):
                word = word_list[word_idx]
                sentence_words.append(word)
                word_idx += 1

                # Check if we've captured the sentence
                current_text = " ".join([w.word for w in sentence_words]).strip()
                if sentence_text in current_text or current_text in sentence_text:
                    if word_idx >= len(word_list) or len(current_text) >= len(sentence_text) * 0.9:
                        break

            if sentence_words:
                chunks.append(sentence_words)

        return chunks

    except Exception as e:
        logger.error(f"Sentence chunking failed: {str(e)}")
        # Fallback to single chunk
        return [words]


def chunk_by_semantic(words: List[WordInput], nlp, max_words: int = 15) -> List[List[WordInput]]:
    """
    Chunk words by semantic boundaries using spaCy

    Args:
        words: List of words with timestamps
        nlp: spaCy model
        max_words: Maximum words per chunk

    Returns:
        List of word groups representing semantic chunks
    """
    try:
        text = " ".join([w.word for w in words])
        doc = nlp(text)

        chunks = []
        current_chunk = []

        for i, token in enumerate(doc):
            if i < len(words):
                current_chunk.append(words[i])

                # Check for semantic boundaries
                is_boundary = (
                    token.is_sent_end or  # Sentence end
                    token.dep_ in ["punct", "ROOT"] or  # Punctuation or root
                    len(current_chunk) >= max_words  # Max words reached
                )

                if is_boundary and current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []

        # Add remaining words
        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [words]

    except Exception as e:
        logger.error(f"Semantic chunking failed: {str(e)}")
        # Fallback to fixed-size chunks
        return [words[i:i + max_words] for i in range(0, len(words), max_words)]


def chunk_by_duration(words: List[WordInput], max_duration: float, min_duration: float) -> List[List[WordInput]]:
    """
    Chunk words by fixed duration

    Args:
        words: List of words with timestamps
        max_duration: Maximum duration per chunk
        min_duration: Minimum duration per chunk

    Returns:
        List of word groups based on duration
    """
    chunks = []
    current_chunk = []
    chunk_start = None

    for word in words:
        if not current_chunk:
            chunk_start = word.start

        current_chunk.append(word)
        duration = word.end - chunk_start

        # Check if we should close this chunk
        if duration >= max_duration:
            chunks.append(current_chunk)
            current_chunk = []
            chunk_start = None

    # Handle remaining words
    if current_chunk:
        # If too short, merge with previous chunk
        if chunks and (current_chunk[0].start - chunks[-1][-1].end) < min_duration:
            chunks[-1].extend(current_chunk)
        else:
            chunks.append(current_chunk)

    return chunks if chunks else [words]


def chunk_hybrid(
    words: List[WordInput],
    language: str,
    max_duration: float,
    min_duration: float,
    max_words: int
) -> List[List[WordInput]]:
    """
    Hybrid chunking combining semantic and duration constraints

    Args:
        words: List of words with timestamps
        language: Language code
        max_duration: Maximum duration per chunk
        min_duration: Minimum duration per chunk
        max_words: Maximum words per chunk

    Returns:
        List of word groups using hybrid strategy
    """
    nlp = load_spacy_model(language)
    text = " ".join([w.word for w in words])

    # First, try sentence boundaries
    try:
        doc = nlp(text)
        chunks = []
        current_chunk = []
        chunk_start = None

        for i, token in enumerate(doc):
            if i >= len(words):
                break

            word = words[i]

            if not current_chunk:
                chunk_start = word.start

            current_chunk.append(word)
            duration = word.end - chunk_start

            # Check boundaries: sentence end OR max duration OR max words
            should_break = (
                (token.is_sent_end or token.text in ['.', '!', '?']) and duration >= min_duration
            ) or duration >= max_duration or len(current_chunk) >= max_words

            if should_break and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                chunk_start = None

        if current_chunk:
            # Merge short final chunk with previous if exists
            if chunks and (current_chunk[0].start - chunks[-1][-1].end) < min_duration:
                chunks[-1].extend(current_chunk)
            else:
                chunks.append(current_chunk)

        return chunks if chunks else [words]

    except Exception as e:
        logger.error(f"Hybrid chunking failed: {str(e)}")
        # Fallback to duration-based chunking
        return chunk_by_duration(words, max_duration, min_duration)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        Service status and loaded models
    """
    return HealthResponse(
        status="healthy",
        models_loaded=list(_nlp_models.keys()),
        nltk_available=True
    )


@app.post("/chunk", response_model=ChunkResponse)
async def chunk_transcript(request: ChunkRequest):
    """
    Chunk transcript words into semantic units

    Args:
        request: Chunking request with words and parameters

    Returns:
        Chunked transcript with preserved timestamps

    Raises:
        HTTPException: If chunking fails
    """
    try:
        logger.info(f"Chunking {len(request.words)} words using {request.strategy} strategy")

        # Select chunking strategy
        if request.strategy == ChunkingStrategy.SENTENCE:
            text = " ".join([w.word for w in request.words])
            word_groups = chunk_by_sentences(text, request.words, request.language)

        elif request.strategy == ChunkingStrategy.SEMANTIC:
            nlp = load_spacy_model(request.language)
            word_groups = chunk_by_semantic(request.words, nlp, request.max_words)

        elif request.strategy == ChunkingStrategy.FIXED_DURATION:
            word_groups = chunk_by_duration(request.words, request.max_duration, request.min_duration)

        else:  # HYBRID (default)
            word_groups = chunk_hybrid(
                request.words,
                request.language,
                request.max_duration,
                request.min_duration,
                request.max_words
            )

        # Build response chunks
        chunks = []
        for word_group in word_groups:
            if not word_group:
                continue

            chunk_text = " ".join([w.word for w in word_group]).strip()
            chunk_start = word_group[0].start
            chunk_end = word_group[-1].end
            duration = chunk_end - chunk_start

            chunks.append(ChunkOutput(
                text=chunk_text,
                start=chunk_start,
                end=chunk_end,
                words=word_group,
                word_count=len(word_group),
                duration=duration
            ))

        total_duration = request.words[-1].end - request.words[0].start if request.words else 0

        logger.info(f"Chunking complete: {len(chunks)} chunks created")

        return ChunkResponse(
            chunks=chunks,
            total_chunks=len(chunks),
            total_duration=total_duration,
            strategy_used=request.strategy.value
        )

    except Exception as e:
        logger.error(f"Chunking failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chunking failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Semantic Chunker Service",
        "version": "1.0.0",
        "strategies": [s.value for s in ChunkingStrategy],
        "endpoints": {
            "chunk": "/chunk",
            "health": "/health",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
