# Semantic Chunker Service - Python with spaCy and NLTK
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy language models
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download vi_core_news_lg || python -m spacy download xx_ent_wiki_sm

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('averaged_perceptron_tagger'); nltk.download('maxent_ne_chunker'); nltk.download('words')"

# Copy application code
COPY . .

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8002/health')"

# Run the application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8002"]
